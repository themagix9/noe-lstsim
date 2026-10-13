'use strict';
window.GraphicUpload={
 async optimize(file){
  if(!file||!file.size)throw Error('Bitte eine Bilddatei auswählen.');
  if(file.size>20*1024*1024)throw Error('Bilddatei maximal 20 MB.');
  if(!['image/png','image/jpeg','image/webp'].includes(file.type))throw Error('Bitte PNG, JPEG oder WebP hochladen.');
  let image;
  try{image=await createImageBitmap(file)}catch{throw Error('Bilddatei kann nicht gelesen werden.')}
  try{
   const scale=Math.min(1,512/image.width,256/image.height),canvas=document.createElement('canvas');
   let width=Math.max(1,Math.round(image.width*scale)),height=Math.max(1,Math.round(image.height*scale));
   for(let attempt=0;attempt<10;attempt++){
    canvas.width=width;canvas.height=height;const ctx=canvas.getContext('2d');ctx.imageSmoothingEnabled=true;ctx.imageSmoothingQuality='high';ctx.drawImage(image,0,0,width,height);
    const blob=await new Promise(resolve=>canvas.toBlob(resolve,'image/png'));
    if(!blob)throw Error('Bild kann nicht als PNG gespeichert werden.');
    if(blob.size<=512*1024)return blob;
    width=Math.max(1,Math.floor(width*.75));height=Math.max(1,Math.floor(height*.75));
   }
   throw Error('Bild konnte nicht ausreichend verkleinert werden.');
  }finally{image.close()}
 }
};
