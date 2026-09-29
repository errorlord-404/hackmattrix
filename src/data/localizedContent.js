export const local = (language, english, hindi) => language === 'hi' ? hindi : english

export const dateText = {
  sowing: { en: '15 Nov 2024', hi: '15 नवम्बर 2024' },
  irrigation: { en: '21 May 2025', hi: '21 मई 2025' },
  harvest: { en: '20 March 2025', hi: '20 मार्च 2025' },
}

export const units = {
  acre: { en: 'Acres', hi: 'एकड़' }, quintal: { en: 'Quintal', hi: 'क्विंटल' }, perAcre: { en: 'per acre', hi: 'प्रति एकड़' }, litresAcre: { en: 'litres/acre', hi: 'लीटर/एकड़' }, kilogramHectare: { en: 'kg/ha', hi: 'किग्रा/हेक्टेयर' },
}
