import { useRef, useState } from 'react'
import { SPEECH_LOCALES } from '../i18n.js'

// Browser Web Speech API: STT for the question, TTS for the answer.
// Zero quota risk — no cloud speech service involved (spec §3).
export default function VoiceButton({ language, onTranscript, t }) {
  const [listening, setListening] = useState(false)
  const recognitionRef = useRef(null)

  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition
  if (!Recognition) return null // unsupported browser: voice quietly hidden

  const start = () => {
    const rec = new Recognition()
    rec.lang = SPEECH_LOCALES[language] || 'en-IN'
    rec.interimResults = false
    rec.maxAlternatives = 1
    rec.onresult = (e) => {
      const transcript = e.results[0][0].transcript
      setListening(false)
      onTranscript(transcript)
    }
    rec.onerror = () => setListening(false)
    rec.onend = () => setListening(false)
    recognitionRef.current = rec
    setListening(true)
    rec.start()
  }

  const stop = () => {
    recognitionRef.current?.stop()
    setListening(false)
  }

  return (
    <button
      type="button"
      onClick={listening ? stop : start}
      className={`shrink-0 w-11 h-11 rounded-full text-xl flex items-center justify-center transition
        ${listening ? 'bg-red-600 animate-pulse text-white' : 'bg-emerald-700 hover:bg-emerald-600 text-white'}`}
      title={listening ? t.listening : t.tapToSpeak}
    >
      🎤
    </button>
  )
}

export function speak(text, language) {
  if (!window.speechSynthesis) return
  window.speechSynthesis.cancel()
  const utterance = new SpeechSynthesisUtterance(text)
  utterance.lang = SPEECH_LOCALES[language] || 'en-IN'
  window.speechSynthesis.speak(utterance)
}
