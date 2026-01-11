const functions = require("firebase-functions");
const { GoogleGenAI } = require("@google/genai");

exports.nano = functions.https.onRequest(async (req, res) => {
  try {
    const apiKey = functions.config().gemini.key;
    const ai = new GoogleGenAI({ apiKey });

    const prompt = req.body?.prompt || "흰 배경에 상품 사진 스타일의 이미지 만들어줘";

    const out = await ai.models.generateContent({
      model: "gemini-3-pro-image-preview",   // = 나노바나나 Pro
      contents: prompt,
    });

    // 결과에서 이미지(base64)만 뽑아서 반환
    const parts = out.candidates?.[0]?.content?.parts || [];
    const images = parts
      .filter(p => p.inlineData?.data)
      .map(p => ({
        mimeType: p.inlineData.mimeType,
        base64: p.inlineData.data
      }));

    res.json({ ok: true, images });
  } catch (e) {
    res.status(500).json({ ok: false, error: String(e.message || e) });
  }
});
