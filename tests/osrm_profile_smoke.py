"""Exercise the actual Lua profile with OSRM on a tiny synthetic OSM network."""
import json
import os
from pathlib import Path
import socket
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
            print('Actual OSRM profile: A=130, S=100, urban=50, limit=30, rural=100; route and matrix agree.')
        finally:subprocess.run(['docker','rm','-f',name],check=False)

if __name__=='__main__':main()
