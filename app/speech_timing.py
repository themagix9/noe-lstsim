"""Shorten only near-silent gaps; never time-stretch speech or alter its pitch."""
from array import array
import io
import math
import sys
import wave

def natural_pauses(raw):
    with wave.open(io.BytesIO(raw),'rb') as wav:
        if wav.getnchannels()!=1 or wav.getsampwidth()!=2:return raw
        rate=wav.getframerate();pcm=array('h',wav.readframes(wav.getnframes()))
    if sys.byteorder!='little':pcm.byteswap()
    size=max(1,rate//100);quiet=[]
    # A conservative -52 dBFS threshold preserves breath and quiet consonants.
    for start in range(0,len(pcm),size):
        block=pcm[start:start+size]
        quiet.append(math.sqrt(sum(int(v)**2 for v in block)/len(block))<80)
    cuts=[];i=0
    while i<len(quiet):
        if not quiet[i]:i+=1;continue
        end=i+1
        while end<len(quiet) and quiet[end]:end+=1
        count=end-i;edge=i==0 or end==len(quiet)
        keep=4 if edge else 18
        if count>(keep if edge else 34):
            left=0 if i==0 else keep if end==len(quiet) else keep//2
            right=keep-left;cuts.append(((i+left)*size,min(len(pcm),(end-right)*size)))
        i=end
    if not cuts:return raw
    result=array('h');cursor=0
    for start,end in cuts:result.extend(pcm[cursor:start]);cursor=end
    result.extend(pcm[cursor:])
    if sys.byteorder!='little':result.byteswap()
    out=io.BytesIO()
    with wave.open(out,'wb') as wav:
        wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(rate);wav.writeframes(result.tobytes())
    return out.getvalue()
