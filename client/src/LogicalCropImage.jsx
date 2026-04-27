import React, { useRef, useEffect, useState } from 'react';

const LogicalCropImage = ({ src, cropCoords }) => {
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
      canvas.width = sWidth;
      canvas.height = sHeight;

      ctx.clearRect(0, 0, sWidth, sHeight);
      ctx.drawImage(img, sx, sy, sWidth, sHeight, 0, 0, sWidth, sHeight);

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