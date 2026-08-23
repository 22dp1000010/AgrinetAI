import { useRef, useState } from 'react'
import { api } from '../api.js'
import { CROPS, CROP_LABELS } from '../i18n.js'
import MapPicker from '../components/MapPicker.jsx'
import ProvenanceStrip from '../components/ProvenanceStrip.jsx'
import AdvisoryCard from '../components/AdvisoryCard.jsx'
import DiagnosisCard from '../components/DiagnosisCard.jsx'
import VoiceButton, { speak } from '../components/VoiceButton.jsx'

const WARANGAL = [17.98, 79.53]

export default function Farmer({ node, language, t }) {
  const [position, setPosition] = useState(WARANGAL)
  const [crop, setCrop] = useState('paddy')
  const [advisory, setAdvisory] = useState(null)
  const [advisoryLoading, setAdvisoryLoading] = useState(false)
  const [diagnosis, setDiagnosis] = useState(null)
  const [diagnosisLoading, setDiagnosisLoading] = useState(false)
  const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState(null)
  const [askLoading, setAskLoading] = useState(false)
  const [error, setError] = useState(null)
  const fileRef = useRef(null)

  const cropLabels = CROP_LABELS[language]

  const run = async (setLoading, setResult, fn) => {
    setError(null)
    setLoading(true)
    try {
      setResult(await fn())
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const getAdvisory = () =>
    run(setAdvisoryLoading, setAdvisory, () =>
      api.getAdvisory(node, { lat: position[0], lon: position[1], crop, language }))

  const useMyLocation = () => {
    navigator.geolocation?.getCurrentPosition(
      (p) => setPosition([p.coords.latitude, p.coords.longitude]),
      () => setError('Location unavailable — tap the map instead.'),
    )
  }

  const onLeafUpload = (e) => {
    const image = e.target.files?.[0]
    if (!image) return
    run(setDiagnosisLoading, setDiagnosis, () =>
      api.diagnose(node, { image, crop, language, lat: position[0], lon: position[1] }))
    e.target.value = ''
  }

  const submitQuestion = (q) => {
    const text = (q ?? question).trim()
    if (!text) return
    run(setAskLoading, setAnswer, async () => {
      const res = await api.ask(node, {
        question: text, language, lat: position[0], lon: position[1], crop,
      })
      speak(res.answer, language)
      return res
    })
  }

  return (
    <div className="max-w-md mx-auto space-y-4">
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-xl p-3">
          {error}
        </div>
      )}

      {/* Location + crop + get advisory */}
      <section className="bg-white border border-stone-200 rounded-2xl p-4 space-y-3 shadow-sm">
        <p className="text-sm text-stone-600">
          {t.pickLocation}{' '}
          <button onClick={useMyLocation} className="text-emerald-700 font-medium underline underline-offset-2">
            {t.useMyLocation}
          </button>
        </p>
        <MapPicker position={position} onPick={setPosition} />
        <p className="text-xs text-stone-400">
          📍 {position[0].toFixed(2)}, {position[1].toFixed(2)}
        </p>
        <div className="flex gap-2">
          <select
            value={crop}
            onChange={(e) => setCrop(e.target.value)}
            className="flex-1 border border-stone-300 rounded-xl px-3 py-2.5 text-sm bg-white"
          >
            {CROPS.map((c) => <option key={c} value={c}>{cropLabels[c]}</option>)}
          </select>
        </div>
        <button
          onClick={getAdvisory}
          disabled={advisoryLoading}
          className="w-full bg-emerald-700 hover:bg-emerald-600 disabled:opacity-60 text-white font-semibold rounded-xl py-3 text-base"
        >
          {advisoryLoading ? t.loadingAdvisory : `🌱 ${t.getAdvisory}`}
        </button>
      </section>

      {advisory && (
        <section className="space-y-3">
          <ProvenanceStrip provenance={advisory.provenance} t={t} />
          <AdvisoryCard advisory={advisory} t={t} />
        </section>
      )}

      {/* Leaf diagnosis */}
      <section className="bg-white border border-stone-200 rounded-2xl p-4 space-y-3 shadow-sm">
        <h2 className="font-semibold">🍃 {t.diagnoseTitle}</h2>
        <p className="text-sm text-stone-500">{t.diagnoseHint}</p>
        <input
          ref={fileRef} type="file" accept="image/jpeg,image/png,image/webp"
          capture="environment" onChange={onLeafUpload} className="hidden"
        />
        <button
          onClick={() => fileRef.current?.click()}
          disabled={diagnosisLoading}
          className="w-full border-2 border-dashed border-emerald-300 hover:border-emerald-500 text-emerald-700 rounded-xl py-3 text-sm font-medium disabled:opacity-60"
        >
          {diagnosisLoading ? t.diagnosing : `📷 ${t.uploadLeaf}`}
        </button>
        {diagnosis && <DiagnosisCard result={diagnosis} t={t} />}
      </section>

      {/* Ask (text + voice) */}
      <section className="bg-white border border-stone-200 rounded-2xl p-4 space-y-3 shadow-sm">
        <h2 className="font-semibold">💬 {t.askTitle}</h2>
        <div className="flex gap-2">
          <input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && submitQuestion()}
            placeholder={t.askPlaceholder}
            className="flex-1 border border-stone-300 rounded-xl px-3 py-2.5 text-sm"
          />
          <VoiceButton
            language={language}
            t={t}
            onTranscript={(text) => { setQuestion(text); submitQuestion(text) }}
          />
        </div>
        <button
          onClick={() => submitQuestion()}
          disabled={askLoading || !question.trim()}
          className="w-full bg-stone-800 hover:bg-stone-700 disabled:opacity-50 text-white rounded-xl py-2.5 text-sm font-medium"
        >
          {askLoading ? '…' : t.askButton}
        </button>
        {answer && (
          <div className="bg-stone-50 border border-stone-200 rounded-xl p-3">
            <p className="text-sm text-stone-800">{answer.answer}</p>
            {answer.citations?.length > 0 && (
              <p className="text-xs text-stone-400 mt-2">
                📄 {answer.citations.map((c) => c.source).join(' · ')}
              </p>
            )}
          </div>
        )}
      </section>
    </div>
  )
}
