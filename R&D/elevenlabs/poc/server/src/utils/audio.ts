const MULAW_MAX = 255;
const SIGN_BIT = 0x80;
const QUANT_MASK = 0x0f;
const SEG_MASK = 0x70;
const SEG_SHIFT = 4;
const BIAS = 0x84;

function muLawDecodeSample(uVal: number): number {
  uVal = ~uVal;
  const sign = (uVal & SIGN_BIT) ? -1 : 1;
  let exponent = (uVal & SEG_MASK) >> SEG_SHIFT;
  let mantissa = uVal & QUANT_MASK;
  mantissa = mantissa + 0.5;
  const magnitude = ((mantissa << (exponent + 3)) + BIAS) - BIAS;
  return sign * magnitude;
}

function muLawEncodeSample(sample: number): number {
  let sign = (sample < 0) ? SIGN_BIT : 0;
  sample = Math.abs(sample);

  if (sample > 32635) {
    sample = 32635;
  }

  sample = sample + BIAS;

  let exponent = 7;
  for (let expMask = 0x4000; (sample & expMask) === 0 && exponent > 0; expMask >>= 1) {
    exponent--;
  }

  let mantissa = (sample >> (exponent + 3)) & QUANT_MASK;
  const muLawByte = ~(sign | (exponent << SEG_SHIFT) | mantissa);
  return muLawByte & MULAW_MAX;
}

export function decodeMuLawBase64ToPcm16(base64: string): Buffer {
  const mulaw = Buffer.from(base64, 'base64');
  const pcm = Buffer.alloc(mulaw.length * 2);

  for (let i = 0; i < mulaw.length; i += 1) {
    const decoded = muLawDecodeSample(mulaw[i]);
    pcm.writeInt16LE(decoded, i * 2);
  }

  return pcm;
}

export function encodePcm16ToMuLawBase64(pcm: Buffer): string {
  const samples = pcm.length / 2;
  const mulaw = Buffer.alloc(samples);

  for (let i = 0; i < samples; i += 1) {
    const sample = pcm.readInt16LE(i * 2);
    const encoded = muLawEncodeSample(sample);
    mulaw[i] = encoded;
  }

  return mulaw.toString('base64');
}



