export const fields = [
  {
    id: 'field-1',
    name: 'Wheat Field',
    nameHi: 'गेहूं का खेत',
    nameMr: 'गव्हाचे शेत',
    crop: 'Wheat',
    cropHi: 'गेहूं',
    cropMr: 'गहू',
    area: '2.5 Acres',
    areaHi: '2.5 एकड़',
    areaMr: '२.५ एकर',
    stage: 'Grain Filling',
    stageHi: 'दाना भराव',
    stageMr: 'दाणे भरणे (ओंब्या)',
    moisture: 28,
    status: 'Healthy',
    statusHi: 'स्वस्थ',
    statusMr: 'उत्तम (निरोगी)',
    color: 'bg-primary',
    tone: 'bg-primary-50 text-primary',
  },
  {
    id: 'field-2',
    name: 'Potato Patch',
    nameHi: 'आलू का खेत',
    nameMr: 'बटाट्याचे शेत',
    crop: 'Potato',
    cropHi: 'आलू',
    cropMr: 'बटाटा',
    area: '1.2 Acres',
    areaHi: '1.2 एकड़',
    areaMr: '१.२ एकर',
    stage: 'Tuber Formation',
    stageHi: 'कंद निर्माण',
    stageMr: 'कंद वाढ',
    moisture: 41,
    status: 'Attention',
    statusHi: 'ध्यान दें',
    statusMr: 'लक्ष द्या',
    color: 'bg-warning',
    tone: 'bg-amber-50 text-amber-700',
  },
  {
    id: 'field-3',
    name: 'Mustard Plot',
    nameHi: 'सरसों का खेत',
    nameMr: 'मोहरीचे शेत',
    crop: 'Mustard',
    cropHi: 'सरसों',
    cropMr: 'मोहरी',
    area: '1.0 Acres',
    areaHi: '1.0 एकड़',
    areaMr: '१.० एकर',
    stage: 'Flowering',
    stageHi: 'फूल अवस्था',
    stageMr: 'फुलोरा अवस्था',
    moisture: 32,
    status: 'Healthy',
    statusHi: 'स्वस्थ',
    statusMr: 'उत्तम',
    color: 'bg-primary',
    tone: 'bg-primary-50 text-primary',
  },
];

export const localizeField = (field, language) => {
  if (language === 'mr') {
    return {
      ...field,
      name: field.nameMr || field.nameHi,
      crop: field.cropMr || field.cropHi,
      area: field.areaMr || field.areaHi,
      stage: field.stageMr || field.stageHi,
      status: field.statusMr || field.statusHi,
    };
  }
  if (language === 'hi') {
    return {
      ...field,
      name: field.nameHi,
      crop: field.cropHi,
      area: field.areaHi,
      stage: field.stageHi,
      status: field.statusHi,
    };
  }
  return field;
};


export const timeline = [
  ['Sowing', '15 Nov', true], ['Germination', '22 Nov', true], ['Tillering', '10 Dec', true], ['Stem Extension', '05 Jan', true], ['Heading', '20 Jan', true], ['Grain Filling', '10 Feb', true], ['Harvest', '20 Mar', false],
]
