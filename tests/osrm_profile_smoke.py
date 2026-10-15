"""Exercise the actual Lua profile with OSRM on a tiny synthetic OSM network."""
import json
import os
from pathlib import Path
import socket
import sys
from unittest.mock import patch
import subprocess
import tempfile
import time
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
IMAGE=os.environ.get('OSRM_IMAGE','ghcr.io/project-osrm/osrm-backend:latest')

def run(*args):return subprocess.run(args,check=True)

def main():
    with tempfile.TemporaryDirectory() as directory:
        data=Path(directory);data.chmod(0o777)
        nodes=''.join(f'<node id="{i+1}" lat="48" lon="{16+i*.02}" version="1"/>' for i in range(6))
        specs=[('motorway','A 4',None),('motorway','S 1',None),('residential','',None),('residential','','30'),('primary','','AT:rural')]
        ways=''
        for i,(highway,ref,limit) in enumerate(specs):
            tags=f'<tag k="highway" v="{highway}"/><tag k="ref" v="{ref}"/>'
            if limit:tags+=f'<tag k="maxspeed" v="{limit}"/>'
            ways+=f'<way id="{i+1}" version="1"><nd ref="{i+1}"/><nd ref="{i+2}"/>{tags}</way>'
        (data/'fixture.osm').write_text('<osm version="0.6">'+nodes+ways+'</osm>')
        volumes=['-v',f'{data}:/data','-v',f'{ROOT}/routing/noe-car.lua:/opt/noe-car.lua:ro']
        for command in (['osrm-extract','-p','/opt/noe-car.lua','/data/fixture.osm'],['osrm-partition','/data/fixture.osrm'],['osrm-customize','/data/fixture.osrm']):
            run('docker','run','--rm',*volumes,IMAGE,*command)
        with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        name='noe-osrm-profile-smoke'
        try:
            run('docker','run','-d','--name',name,'-p',f'127.0.0.1:{port}:5000',*volumes,IMAGE,'osrm-routed','--algorithm','mld','/data/fixture.osrm')
            def query(path):
                with urllib.request.urlopen(f'http://127.0.0.1:{port}'+path,timeout=3) as response:return json.load(response)
            for attempt in range(30):
                try:query('/nearest/v1/driving/16.001,48');break
                except Exception:time.sleep(1)
            else:raise AssertionError('OSRM startup timeout')
            for i,expected in enumerate((130,100,50,30,100)):
                start=16+i*.02+.002;end=start+.016
                route=query(f'/route/v1/driving/{start},48;{end},48?overview=full&geometries=geojson&annotations=duration,distance')['routes'][0]
                annotation=route['legs'][0]['annotation']
                speed=sum(annotation['distance'])/sum(annotation['duration'])*3.6
                assert abs(speed-expected)<2,(i,expected,speed)
                matrix=query(f'/table/v1/driving/{start},48;{end},48?sources=0&destinations=1')['durations'][0][0]
                assert abs(matrix-route['duration'])<1,(matrix,route['duration'])
            sys.path.insert(0,str(ROOT/'app'))
            from engine import Engine
            from routing import Router
            with patch.dict(os.environ,{'ROUTING_ENABLED':'0','REINFORCEMENTS_AUTO':'0','PATIENT_EVOLUTION':'0','CALL_AUTO':'0'}):
                engine=Engine(str(data/'simulation'))
            router=Router(data/'routes',url=f'http://127.0.0.1:{port}',enabled=True,backup_url='')
            engine.router=router
            v=next(v for v in engine.state['vehicles'] if v['callsign']=='77/002')
            # 110 metres off the residential road; the chosen road is reachable.
            v.update(lat=48.001,lon=16.045,status='radio')
            job=engine.new_job('transport',manual=True);job.update(accepted=True,lat=48.0007,lon=16.075)
            a={k:v[k] for k in ('lat','lon')};b={k:job[k] for k in ('lat','lon')}
            start=time.monotonic();planned=router.wait_routes([('car',a,b)],timeout=3)['car']
            assert time.monotonic()-start<3
            assert planned['status']=='ready' and planned['recovered']
            engine.dispatch({'job':job['id'],'vehicles':[v['id']],'_planned_routes':{v['id']:{'origin':a,'target':b,'route':planned}}})
            with patch.object(router,'route',side_effect=AssertionError('Departure requested another route')):
                engine.acknowledge(v);assert v['leg']['geometry']
                assert abs(v['lat']-48)<.00001
                clock=engine.state['clock'];before=(v['lat'],v['lon'])
                engine.update_operations(clock+1);assert (v['lat'],v['lon'])!=before
                engine.advance(v);assert v['status']=='enroute' and v['leg']['start']==clock
            for status in ('enroute','transport','radio','duty','acknowledged'):
                v.update(lat=48.001,lon=16.045)
                router.wait_routes([('car',v,b)],timeout=3)
                engine.drive(v,b,status)
                assert v['leg'].get('geometry') and not v['leg'].get('waiting'),status
                before=(v['lat'],v['lon']);engine.update_operations(engine.state['clock']+1)
                assert (v['lat'],v['lon'])!=before,status
            # Real cancellation path: signal off, cached road return reaches home.
            home=engine.home(v);home.update(lat=48,lon=16.045)
            v.update(lat=48.0007,lon=16.075,status='enroute',signal=True)
            router.wait_routes([('home',v,home)],timeout=3)
            engine.command('resource_call',{'job':job['id'],'vehicle':v['id']});call=engine.state['radio_calls'][-1]
            engine.command('cancel_radio',{'job':job['id'],'call':call['id'],'step':'answer'})
            engine.command('cancel_radio',{'job':job['id'],'call':call['id'],'step':'cancel'})
            assert v['status']=='radio' and not v['signal'] and v['leg']['geometry']
            engine.state['clock']=v['leg']['end']+1;engine.update_operations(engine.state['clock']);engine.advance(v)
            assert v['status']=='ready' and abs(v['lon']-home['lon'])<.00001
            router.journeys.join();router.tasks.join();router.db.close();engine.db.close()
            print('Actual OSRM: off-road snap, preflight, no second departure request, motion in 2/4/6/7/9, cancellation return passed.')
            print('Actual OSRM profile: A=130, S=100, urban=50, limit=30, rural=100; route and matrix agree.')
        finally:subprocess.run(['docker','rm','-f',name],check=False)

if __name__=='__main__':main()
