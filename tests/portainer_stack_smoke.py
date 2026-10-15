"""Run Portainer's routing services from a standalone Compose file, no repo mounts.

Use the real prepare command/profile and OSRM phases. Only the input extension
changes to XML for a tiny synthetic fixture instead of the full Austria PBF.
"""
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import time
import urllib.request
import uuid

ROOT=Path(__file__).resolve().parents[1]
IMAGE=os.environ.get('OSRM_IMAGE','ghcr.io/project-osrm/osrm-backend:latest')

def main():
    project='noe-portainer-'+uuid.uuid4().hex[:10]
    env={**os.environ,'CLOUDFLARE_TUNNEL_TOKEN':'ci-validation-placeholder'}
    with tempfile.TemporaryDirectory() as directory:
        folder=Path(directory);stack=folder/'compose.yaml'
        shutil.copyfile(ROOT/'compose.portainer.yaml',stack)
        def run(*args,capture=False,check=True):
            return subprocess.run(args,cwd=folder,env=env,check=check,text=True,stdout=subprocess.PIPE if capture else None)
        base=['docker','compose','-p',project,'-f',str(stack)]
        model=json.loads(run(*base,'config','--format','json',capture=True).stdout)
        assert not (folder/'routing').exists(),'The test must not have the repository profile beside Compose'
        assert not model.get('configs'),'No file-based configs may depend on Portainer checkout paths'
        for name,service in model['services'].items():
            assert not service.get('configs'),name
            assert all(v['type']=='volume' for v in service.get('volumes',[])),name
        # Use raw YAML's block scalar so Compose performs dollar interpolation once.
        prepare=stack.read_text().split('  osm-prepare:\n',1)[1]
        script=prepare.split('    command:\n      - -ec\n      - |\n',1)[1].split('    depends_on:',1)[0]
        script='\n'.join(line[8:] for line in script.rstrip().splitlines())
        assert 'osrm-extract -p /data/noe-car.lua /data/austria.osm.pbf' in script
        with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        override=folder/'fixture.json'
        override.write_text(json.dumps({'services':{
            'osm-prepare':{'command':['-ec',script.replace('/data/austria.osm.pbf','/data/austria.osm')]},
            'osrm':{'ports':[f'127.0.0.1:{port}:5000']}}}))
        compose=base+['-f',str(override)]
        volume=model['volumes']['routing-data']['name'];seed=project+'-seed'
        (folder/'austria.osm').write_text('<osm version="0.6">'
            '<node id="1" lat="48" lon="16" version="1"/>'
            '<node id="2" lat="48" lon="16.01" version="1"/>'
            '<node id="3" lat="48.01" lon="16.01" version="1"/>'
            '<way id="1" version="1"><nd ref="1"/><nd ref="2"/><nd ref="3"/>'
            '<tag k="highway" v="residential"/></way></osm>')
        (folder/'austria.osm.pbf').write_text('CI: fixture already supplied; skip Austria download')
        try:
            run('docker','volume','create',volume)
            run('docker','create','--name',seed,'-v',volume+':/data',IMAGE,'/bin/true')
            for name in ('austria.osm','austria.osm.pbf'):run('docker','cp',str(folder/name),seed+':/data/'+name)
            run('docker','rm',seed)
            run(*compose,'up','-d','osrm')
            for attempt in range(30):
                try:
                    with urllib.request.urlopen(f'http://127.0.0.1:{port}/route/v1/driving/16.001,48;16.01,48.009?overview=full&geometries=geojson',timeout=2) as response:route=json.load(response)
                    if route.get('code')=='Ok':break
                except OSError:pass
                time.sleep(1)
            else:raise AssertionError('Stack OSRM did not serve a route')
            assert route['routes'][0]['distance']>1000 and len(route['routes'][0]['geometry']['coordinates'])>=3
            container=run(*compose,'ps','-q','osrm',capture=True).stdout.strip()
            mounts=json.loads(run('docker','inspect',container,capture=True).stdout)[0]['Mounts']
            assert mounts and all(m['Type']=='volume' for m in mounts),mounts
            run('docker','cp',container+':/data/noe-car.lua',str(folder/'copied-profile.lua'))
            assert (folder/'copied-profile.lua').read_bytes()==(ROOT/'routing/noe-car.lua').read_bytes()
            print('Portainer standalone Compose: no checkout/bind mounts; embedded profile, download skip, extraction, partition, customization and actual road route passed.')
        except Exception:
            run(*compose,'logs','--no-color',check=False);raise
        finally:
            run('docker','rm','-f',seed,check=False)
            run(*compose,'down','--volumes','--remove-orphans',check=False)

if __name__=='__main__':main()
