"""User supplied project graphics; migrate default icons without overwriting custom choices."""
GRAPHICS=[{'id':id,'name':name,'url':'/graphics/'+file,'author':'Julian Böhm','source':'Vom Nutzer am 14.10.2026 als eigene Grafik bereitgestellt','license':'Vom Nutzer für dieses Projekt bereitgestellt'} for id,name,file in [('user-rtw','RTW / RTW-C · Nutzergrafik','rtw-user.png'),('user-nef','NEF · Nutzergrafik','nef-user.png'),('user-nah','Christophorus · Nutzergrafik','christophorus-user.png')]]
DEFAULTS={'RTW':'user-rtw','RTW-C':'user-rtw','NEF':'user-nef','NAH':'user-nah'}
def upgrade(engine):
    if engine.state.get('user_graphics_version')==1:return
    for v in engine.state['vehicles']:
        if v['type'] in DEFAULTS and v.get('graphic') in ('van','box','car','helicopter') and not v.get('graphic_custom'):
            v['graphic']=DEFAULTS[v['type']]
    engine.state['user_graphics_version']=1
