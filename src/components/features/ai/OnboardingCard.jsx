import { ArrowRight, MapPinned, Sprout, Volume2 } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useAIConversation } from '../../../context/AIConversationContext.jsx';

const copy = {
  en: {
    eyebrow: 'YOUR NEXT FARM STEP',
    create_profile: ['Let’s get to know your farm', 'Tell me your name and village so advice can start from the right place.', 'Set up profile'],
    set_location: ['Place your farm on the map', 'Add your location before choosing a field or checking local weather.', 'Add location'],
    create_field: ['Draw your first field', 'Choose a place, trace the corners, and check the acreage before saving.', 'Open field map'],
    review_boundary: ['Check your field boundary', 'A saved boundary is approximate or unclassified. Trace the actual corners before using its area.', 'Review boundary'],
    choose_crop: ['Choose the crop together', 'I can compare crops for this field after you tell me your sowing window and water access.', 'Discuss crops'],
    start_crop_cycle: ['Record this growing season', 'The crop is named, but its planting date and stage are not yet recorded. I can help you add them with your confirmation.', 'Start crop cycle'],
    voice: 'Voice needs setup',
    voiceAction: 'Voice settings',
  },
  hi: {
    eyebrow: 'आपका अगला खेती कदम',
    create_profile: ['पहले अपने खेत के बारे में बताएं', 'अपना नाम और गांव बताएं ताकि सलाह सही जगह से शुरू हो।', 'प्रोफ़ाइल बनाएं'],
    set_location: ['खेत की जगह तय करें', 'खेत चुनने और स्थानीय मौसम देखने से पहले अपना स्थान जोड़ें।', 'स्थान जोड़ें'],
    create_field: ['पहला खेत नक्शे पर बनाएं', 'जगह चुनें, कोने चिन्हित करें और क्षेत्रफल देखकर सहेजें।', 'खेत का नक्शा खोलें'],
    review_boundary: ['खेत की सीमा जांचें', 'सहेजी गई सीमा अनुमानित या अपुष्ट है। सही कोने चिन्हित करें।', 'सीमा जांचें'],
    choose_crop: ['मिलकर फसल चुनें', 'बुवाई का समय और पानी की उपलब्धता बताएं, फिर मैं विकल्पों की तुलना करूंगा।', 'फसलों पर बात करें'],
    start_crop_cycle: ['इस मौसम की फसल दर्ज करें', 'फसल का नाम है, लेकिन बुवाई की तारीख और अवस्था दर्ज नहीं हैं। आपकी पुष्टि के बाद मैं उन्हें जोड़ सकता हूँ।', 'फसल चक्र शुरू करें'],
    voice: 'आवाज़ सेटअप बाकी है',
    voiceAction: 'आवाज़ सेटिंग',
  },
  mr: {
    eyebrow: 'शेतीतील पुढचे पाऊल',
    create_profile: ['तुमच्या शेताची ओळख करूया', 'योग्य सल्ल्यासाठी तुमचे नाव आणि गाव सांगा.', 'प्रोफाइल तयार करा'],
    set_location: ['शेताचे ठिकाण ठरवा', 'शेत निवडण्यापूर्वी आणि स्थानिक हवामान पाहण्यापूर्वी ठिकाण जोडा.', 'ठिकाण जोडा'],
    create_field: ['पहिले शेत नकाशावर आखा', 'ठिकाण निवडा, कोपरे चिन्हांकित करा आणि क्षेत्र तपासून जतन करा.', 'शेताचा नकाशा उघडा'],
    review_boundary: ['शेताची सीमा तपासा', 'जतन केलेली सीमा अंदाजे किंवा अपुष्ट आहे. खरे कोपरे चिन्हांकित करा.', 'सीमा तपासा'],
    choose_crop: ['मिळून पीक निवडूया', 'पेरणीचा काळ आणि पाण्याची उपलब्धता सांगा, मग पर्याय तुलना करू.', 'पिकांवर चर्चा करा'],
    start_crop_cycle: ['या हंगामाची नोंद करा', 'पिकाचे नाव आहे, पण पेरणीची तारीख आणि अवस्था नोंदलेली नाही. तुमच्या संमतीने ती जोडता येईल.', 'पीक चक्र सुरू करा'],
    voice: 'आवाज सेटअप बाकी आहे',
    voiceAction: 'आवाज सेटिंग',
  },
};

const destination = {
  create_profile: '/settings#profile',
  set_location: '/settings#profile',
  create_field: '/fields?add=1',
  review_boundary: '/fields?review=1',
};

export default function OnboardingCard() {
  const { onboarding, onboardingError, refreshOnboardingStatus, language, sendText, processing } = useAIConversation();
  const localized = copy[language] || copy.en;
  const step = onboarding?.next_setup_step;
  const stepCopy = localized[step];
  if (!stepCopy && !onboardingError && (onboarding?.voice_configured !== false || !onboarding)) return null;

  return <section aria-label="Farm setup guidance" className="relative overflow-hidden rounded-2xl border border-emerald-200 bg-[#f3f8ed] p-4 shadow-sm sm:p-5">
    <div aria-hidden="true" className="pointer-events-none absolute -right-10 -top-14 size-44 rounded-full border-[22px] border-emerald-100/75" />
    {stepCopy && <div className="relative flex items-start gap-3"><span className="grid size-10 shrink-0 place-items-center rounded-xl bg-[#1d6b45] text-white"><MapPinned size={20} /></span><div className="min-w-0 flex-1"><p className="text-[10px] font-bold tracking-[0.16em] text-[#477355]">{localized.eyebrow}</p><h2 className="mt-1 text-base font-bold leading-6 text-[#173f2a]">{stepCopy[0]}</h2><p className="mt-1 text-xs leading-5 text-[#4c6753]">{stepCopy[1]}</p><div className="mt-3 flex flex-wrap gap-2">{destination[step] ? <Link to={destination[step]} className="inline-flex items-center gap-1.5 rounded-lg bg-[#1d6b45] px-3 py-2 text-xs font-semibold text-white hover:bg-[#145131] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#1d6b45]">{stepCopy[2]}<ArrowRight size={14} /></Link> : <button type="button" disabled={processing} onClick={() => sendText(step === 'start_crop_cycle' ? 'Help me record the planting date and stage for my selected field. Ask what you need and confirm the exact record before saving.' : 'Help me compare crops for my recorded field and ask what you need first.')} className="inline-flex items-center gap-1.5 rounded-lg bg-[#1d6b45] px-3 py-2 text-xs font-semibold text-white hover:bg-[#145131] disabled:opacity-50"><Sprout size={14} />{stepCopy[2]}</button>}</div></div></div>}
    {onboarding?.voice_configured === false && <div className={`relative flex flex-wrap items-center gap-2 text-xs text-amber-900 ${stepCopy ? 'mt-4 border-t border-emerald-200 pt-3' : ''}`}><Volume2 size={15} /><span>{localized.voice}</span><Link className="font-semibold underline underline-offset-2" to="/settings#voice">{localized.voiceAction}</Link></div>}
    {onboardingError && <div className={`relative flex items-center gap-2 text-xs text-amber-900 ${stepCopy ? 'mt-4 border-t border-emerald-200 pt-3' : ''}`}><span>Farm setup status is unavailable.</span><button type="button" onClick={refreshOnboardingStatus} className="font-semibold underline underline-offset-2">Retry</button></div>}
  </section>;
}
