"""Original pixel strawberry icon; no external image assets."""
from pathlib import Path
import struct,zlib
root=Path(__file__).resolve().parents[1]/'AniStream.Fresa'/'Assets'
root.mkdir(parents=True,exist_ok=True)
rows=[
'       gg       ',
'   gg gGGg gg   ',
'    gGGGGGGg    ',
'  pppgGGGGgppp  ',
' pPPPPgGGgPPPPp ',
'pPPPPPPPPPPPPPPp',
'pPPyPPPPPPyPPPPp',
'pPPPPPyPPPPPPPPp',
' pPPPPPPPPPPyPp ',
' pPPyPPPPyPPPPp ',
'  pPPPPPPPPPPp  ',
'   pPPPyPPPPp   ',
'    pPPPPyPp    ',
'     pPPPPp     ',
'      pPPp      ',
'       pp       ',
]
colors={' ':(0,0,0,0),'p':(177,74,114,255),'P':(245,167,193,255),'y':(255,246,213,255),'g':(107,153,116,255),'G':(167,209,172,255)}
size=256
raw=b''.join(b'\0'+b''.join(bytes(colors[rows[y//16][x//16]]) for x in range(size)) for y in range(size))
def chunk(t,d):return struct.pack('>I',len(d))+t+d+struct.pack('>I',zlib.crc32(t+d)&0xffffffff)
png=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',size,size,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(raw,9))+chunk(b'IEND',b'')
(root/'fresa.ico').write_bytes(struct.pack('<HHH',0,1,1)+struct.pack('<BBBBHHII',0,0,0,0,1,32,len(png),22)+png)
svg=['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" shape-rendering="crispEdges">']
for y,row in enumerate(rows):
 for x,c in enumerate(row):
  if c!=' ':svg.append(f'<rect x="{x}" y="{y}" width="1" height="1" fill="#{colors[c][0]:02x}{colors[c][1]:02x}{colors[c][2]:02x}"/>')
svg.append('</svg>');(root/'fresa.svg').write_text('\n'.join(svg))
