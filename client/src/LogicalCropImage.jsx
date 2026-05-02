import React, { useRef, useEffect, useState } from 'react';

const LogicalCropImage = ({ src, cropCoords, displayScale = 1 }) => {
  const canvasRef = useRef(null);
  const imgRef = useRef(null);
  const [croppedDataUrl, setCroppedDataUrl] = useState('');

  useEffect(() => {
    if (!imgRef.current || !canvasRef.current || !cropCoords) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    const img = imgRef.current;

    if (!ctx) return;

    const drawCrop = () => {
      const { sx, sy, sWidth, sHeight } = cropCoords;
      const dw = Math.max(1, Math.floor(sWidth * displayScale));
      const dh = Math.max(1, Math.floor(sHeight * displayScale));
      canvas.width = dw;
      canvas.height = dh;

      ctx.clearRect(0, 0, dw, dh);
      ctx.imageSmoothingEnabled = false;
      ctx.drawImage(img, sx, sy, sWidth, sHeight, 0, 0, dw, dh);

      const dataUrl = canvas.toDataURL('image/png');
      setCroppedDataUrl(dataUrl);
    };

    if (img.complete && img.naturalWidth > 0) {
      drawCrop();
      return;
    }

    img.onload = drawCrop;

    return () => {
      img.onload = null;
    };
  }, [src, cropCoords]);

  return (
    <>
      <img ref={imgRef} src={src} alt="original sprite sheet source" style={{ display: 'none' }} />
      <canvas ref={canvasRef} style={{ display: 'none' }} />
      
      {croppedDataUrl ? (
        <img src={croppedDataUrl} alt="the logically cropped result" style={{ imageRendering: 'pixelated' }} />
      ) : (
        <p>Loading crop...</p>
      )}
    </>
  );
};

export default LogicalCropImage;