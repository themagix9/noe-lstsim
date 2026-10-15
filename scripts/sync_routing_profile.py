"""Embed the canonical Lua profile so Portainer needs no host-path mounts."""
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
START='        # BEGIN embedded NOe car profile\n'
END='        # END embedded NOe car profile\n'

def embedded():
    # Compose unescapes $$; the quoted shell heredoc must receive literal Lua.
    profile=(ROOT/'routing/noe-car.lua').read_text().replace('$','$$')
    return START+"        cat > /data/noe-car.lua <<'NOE_CAR_PROFILE'\n"+''.join('        '+line+'\n' for line in profile.splitlines())+'        NOE_CAR_PROFILE\n'+END

def sync(check=False):
    for name in ('compose.portainer.yaml','compose.yaml'):
        path=ROOT/name;text=path.read_text();a=text.index(START);b=text.index(END,a)+len(END)
        updated=text[:a]+embedded()+text[b:]
        if check:
            if updated!=text:raise SystemExit(f'{name}: embedded routing profile differs; run python scripts/sync_routing_profile.py')
        else:path.write_text(updated)

if __name__=='__main__':sync('--check' in sys.argv)
