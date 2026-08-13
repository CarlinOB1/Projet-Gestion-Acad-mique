import { useState, useRef, useEffect } from 'react'

// ─── Types ───────────────────────────────────────────────────────────────────

type CourseType = 'CM' | 'TD' | 'TP' | 'conflict'

interface Session {
  id: string
  type: CourseType
  module: string
  class: string
  teacher: string
}

interface Cell {
  sessions: Session[]
}

interface RoomData {
  id: string
  label: string
  building: string
  capacity: number
  grid: Record<string, Record<string, Cell>>
}

type AppScreen = 'default' | 'panel' | 'empty'

// ─── Constants ────────────────────────────────────────────────────────────────

const DAYS = [
  { short: 'Lun', date: '11 août' },
  { short: 'Mar', date: '12 août' },
  { short: 'Mer', date: '13 août' },
  { short: 'Jeu', date: '14 août' },
  { short: 'Ven', date: '15 août' },
  { short: 'Sam', date: '16 août' },
]

const SLOTS = [
  { id: 'slot1', label: '9h – 11h' },
  { id: 'slot2', label: '11h15 – 13h15' },
  { id: 'slot3', label: '14h15 – 16h15' },
]

const ROOMS: RoomData[] = [
  {
    id: 'amphi-a',
    label: 'Amphi A',
    building: 'Bâtiment principal',
    capacity: 120,
    grid: {
      slot1: {
        Lun: {
          sessions: [
            { id: 's1', type: 'CM', module: 'Analyse 3', class: 'L3 Mathématiques', teacher: 'Dr. Martin' },
          ],
        },
        Mar: { sessions: [] },
        Mer: {
          sessions: [
            { id: 's2', type: 'TD', module: 'Probabilités', class: 'L3 Statistiques', teacher: 'Dr. Dupont' },
          ],
        },
        Jeu: { sessions: [] },
        Ven: { sessions: [] },
        Sam: { sessions: [] },
      },
      slot2: {
        Lun: { sessions: [] },
        Mar: {
          sessions: [
            { id: 's3', type: 'CM', module: 'Algèbre linéaire', class: 'L2 Maths-Info', teacher: 'Pr. Legrand' },
          ],
        },
        Mer: { sessions: [] },
        Jeu: {
          sessions: [
            { id: 's4', type: 'CM', module: 'Topologie', class: 'M1 Mathématiques', teacher: 'Dr. Bernard' },
            { id: 's5', type: 'CM', module: 'Géométrie diff.', class: 'M1 Mathématiques', teacher: 'Pr. Simon' },
          ],
        },
        Ven: {
          sessions: [
            { id: 's6', type: 'TP', module: 'Algorithmique', class: 'M1 Informatique', teacher: 'Dr. Leblanc' },
          ],
        },
        Sam: { sessions: [] },
      },
      slot3: {
        Lun: { sessions: [] },
        Mar: { sessions: [] },
        Mer: {
          sessions: [
            { id: 's7', type: 'TD', module: 'Statistiques inf.', class: 'L3 Économie', teacher: 'Dr. Moreau' },
          ],
        },
        Jeu: { sessions: [] },
        Ven: {
          sessions: [
            { id: 's8', type: 'TP', module: 'Systèmes d\'exploitation', class: 'L3 Informatique', teacher: 'Pr. Fontaine' },
          ],
        },
        Sam: { sessions: [] },
      },
    },
  },
  {
    id: 'salle-tp-12',
    label: 'Salle TP 12',
    building: 'Bâtiment B',
    capacity: 24,
    grid: {
      slot1: { Lun: { sessions: [] }, Mar: { sessions: [] }, Mer: { sessions: [] }, Jeu: { sessions: [] }, Ven: { sessions: [] }, Sam: { sessions: [] } },
      slot2: { Lun: { sessions: [] }, Mar: { sessions: [] }, Mer: { sessions: [] }, Jeu: { sessions: [] }, Ven: { sessions: [] }, Sam: { sessions: [] } },
      slot3: { Lun: { sessions: [] }, Mar: { sessions: [] }, Mer: { sessions: [] }, Jeu: { sessions: [] }, Ven: { sessions: [] }, Sam: { sessions: [] } },
    },
  },
  {
    id: 'salle-td-5',
    label: 'Salle TD 5',
    building: 'Bâtiment principal',
    capacity: 36,
    grid: {
      slot1: {
        Lun: { sessions: [{ id: 't1', type: 'TD', module: 'Macroéconomie', class: 'L2 Économie', teacher: 'Dr. Petit' }] },
        Mar: { sessions: [] },
        Mer: { sessions: [{ id: 't2', type: 'TD', module: 'Comptabilité', class: 'L3 Gestion', teacher: 'Pr. Rousseau' }] },
        Jeu: { sessions: [] },
        Ven: { sessions: [] },
        Sam: { sessions: [] },
      },
      slot2: {
        Lun: { sessions: [] },
        Mar: { sessions: [{ id: 't3', type: 'TP', module: 'Méthodes quantitatives', class: 'M1 Économie', teacher: 'Dr. Laurent' }] },
        Mer: { sessions: [] },
        Jeu: { sessions: [{ id: 't4', type: 'TD', module: 'Finance d\'entreprise', class: 'L3 Gestion', teacher: 'Dr. Garcia' }] },
        Ven: { sessions: [] },
        Sam: { sessions: [] },
      },
      slot3: {
        Lun: { sessions: [{ id: 't5', type: 'TD', module: 'Économétrie', class: 'M1 Économie', teacher: 'Pr. Michel' }] },
        Mar: { sessions: [] },
        Mer: { sessions: [] },
        Jeu: { sessions: [] },
        Ven: { sessions: [{ id: 't6', type: 'TD', module: 'Droit des affaires', class: 'L3 Gestion', teacher: 'Dr. Blanc' }] },
        Sam: { sessions: [] },
      },
    },
  },
]

const FILIERES = ['Mathématiques', 'Informatique', 'Économie', 'Gestion']
const CLASSES: Record<string, string[]> = {
  'Mathématiques': ['L2 Maths', 'L3 Maths', 'M1 Maths'],
  'Informatique': ['L2 Info', 'L3 Info', 'M1 Info'],
  'Économie': ['L2 Économie', 'L3 Économie', 'M1 Économie'],
  'Gestion': ['L2 Gestion', 'L3 Gestion', 'M1 Gestion'],
}
const MODULES: Record<string, string[]> = {
  'L2 Maths': ['Algèbre', 'Analyse 1'],
  'L3 Maths': ['Analyse 3', 'Topologie'],
  'M1 Maths': ['Géométrie diff.', 'Probabilités avancées'],
  'L2 Info': ['Algorithmique', 'Programmation'],
  'L3 Info': ['Systèmes', 'Réseaux'],
  'M1 Info': ['Machine Learning', 'Compilation'],
  'L2 Économie': ['Micro 2', 'Macro 2'],
  'L3 Économie': ['Économétrie', 'Finance'],
  'M1 Économie': ['Économie internationale', 'Séries temporelles'],
  'L2 Gestion': ['Comptabilité', 'Management'],
  'L3 Gestion': ['Stratégie', 'Contrôle de gestion'],
  'M1 Gestion': ['Audit', 'Fiscalité'],
}
const TEACHERS = ['Dr. Martin', 'Dr. Dupont', 'Pr. Legrand', 'Dr. Bernard', 'Pr. Simon', 'Dr. Leblanc', 'Dr. Moreau', 'Pr. Fontaine']

// ─── Style helpers ────────────────────────────────────────────────────────────

const typeStyles: Record<CourseType, { bg: string; border: string; text: string; dot: string }> = {
  CM: { bg: 'bg-blue-50', border: 'border-blue-200', text: 'text-blue-900', dot: 'bg-blue-400' },
  TD: { bg: 'bg-emerald-50', border: 'border-emerald-200', text: 'text-emerald-900', dot: 'bg-emerald-400' },
  TP: { bg: 'bg-violet-50', border: 'border-violet-200', text: 'text-violet-900', dot: 'bg-violet-400' },
  conflict: { bg: 'bg-red-50', border: 'border-red-200', text: 'text-red-900', dot: 'bg-red-400' },
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function AlertBanner() {
  return (
    <div className="flex items-center gap-2.5 px-4 py-2.5 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
      <svg className="w-4 h-4 flex-shrink-0 text-red-500" viewBox="0 0 16 16" fill="none">
        <path d="M7.02 2.76a1.1 1.1 0 0 1 1.96 0l5.33 9.49A1.1 1.1 0 0 1 13.33 14H2.67a1.1 1.1 0 0 1-.98-1.75L7.02 2.76Z" stroke="currentColor" strokeWidth="1.25" strokeLinejoin="round"/>
        <path d="M8 6.5v3M8 11.5h.01" stroke="currentColor" strokeWidth="1.25" strokeLinecap="round"/>
      </svg>
      <span><strong>Conflit détecté :</strong> deux séances se chevauchent sur ce créneau (Jeu 14 août · 11h15 – 13h15).</span>
    </div>
  )
}

function ConflictCell({ sessions }: { sessions: Session[] }) {
  return (
    <div className="h-full w-full flex flex-col gap-1 p-2 bg-red-50 border border-red-200 rounded-lg">
      <div className="flex items-center gap-1 mb-0.5">
        <svg className="w-3 h-3 text-red-500 flex-shrink-0" viewBox="0 0 16 16" fill="none">
          <path d="M7.02 2.76a1.1 1.1 0 0 1 1.96 0l5.33 9.49A1.1 1.1 0 0 1 13.33 14H2.67a1.1 1.1 0 0 1-.98-1.75L7.02 2.76Z" stroke="currentColor" strokeWidth="1.25" strokeLinejoin="round"/>
          <path d="M8 6.5v2.5M8 11h.01" stroke="currentColor" strokeWidth="1.25" strokeLinecap="round"/>
        </svg>
        <span className="text-[10px] font-semibold text-red-600 uppercase tracking-wide">Conflit</span>
      </div>
      {sessions.map((s) => (
        <div key={s.id} className="text-red-700 leading-tight">
          <div className="text-[10px] font-semibold">{s.module}</div>
          <div className="text-[9px] opacity-75">{s.class}</div>
        </div>
      ))}
    </div>
  )
}

function SessionCell({ session }: { session: Session }) {
  const st = typeStyles[session.type]
  return (
    <div className={`h-full w-full flex flex-col gap-0.5 p-2 ${st.bg} border ${st.border} rounded-lg`}>
      <div className="flex items-center gap-1.5">
        <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[9px] font-semibold uppercase tracking-wide ${st.bg} ${st.text} border ${st.border}`}>
          {session.type}
        </span>
      </div>
      <div className={`text-[11px] font-semibold ${st.text} leading-tight mt-0.5`}>{session.module}</div>
      <div className="text-[10px] text-gray-500 leading-tight">{session.class}</div>
      <div className="text-[10px] text-gray-400 leading-tight">{session.teacher}</div>
    </div>
  )
}

function EmptyCell({
  onHover,
  isHovered,
  onClick,
}: {
  onHover: (v: boolean) => void
  isHovered: boolean
  onClick: () => void
}) {
  return (
    <button
      className={`h-full w-full flex flex-col items-center justify-center gap-1 rounded-lg border transition-all duration-150 cursor-pointer ${
        isHovered
          ? 'border-blue-400 bg-blue-50/60'
          : 'border-dashed border-gray-200 bg-transparent'
      }`}
      onMouseEnter={() => onHover(true)}
      onMouseLeave={() => onHover(false)}
      onClick={onClick}
      aria-label="Ajouter une séance"
    >
      <svg
        className={`w-4 h-4 transition-colors ${isHovered ? 'text-blue-400' : 'text-gray-300'}`}
        fill="none"
        viewBox="0 0 16 16"
      >
        <path d="M8 3v10M3 8h10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
      </svg>
      {isHovered && <span className="text-[10px] text-blue-400 font-medium">Affecter</span>}
    </button>
  )
}

interface PanelProps {
  slot: string
  day: string
  anchorRef: React.RefObject<HTMLDivElement | null>
  onClose: () => void
}

function QuickPanel({ slot, day, anchorRef, onClose }: PanelProps) {
  const [filiere, setFiliere] = useState('')
  const [classe, setClasse] = useState('')
  const [module, setModule] = useState('')
  const [teacher, setTeacher] = useState('')
  const panelRef = useRef<HTMLDivElement>(null)

  const classes = filiere ? CLASSES[filiere] || [] : []
  const modules = classe ? MODULES[classe] || [] : []

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        onClose()
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [onClose])

  return (
    <div
      ref={panelRef}
      className="absolute z-50 w-72 bg-white border border-gray-200 rounded-xl shadow-lg p-4 flex flex-col gap-3"
      style={{ top: '50%', left: '105%', transform: 'translateY(-50%)' }}
    >
      <div className="flex items-center justify-between mb-0.5">
        <div>
          <div className="text-sm font-semibold text-gray-800">Affectation rapide</div>
          <div className="text-[11px] text-gray-400">{day} · {slot}</div>
        </div>
        <button onClick={onClose} className="text-gray-300 hover:text-gray-500 transition-colors">
          <svg className="w-4 h-4" fill="none" viewBox="0 0 16 16">
            <path d="M4 4l8 8M12 4l-8 8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
          </svg>
        </button>
      </div>

      <div className="flex flex-col gap-2">
        <div className="flex flex-col gap-1">
          <label className="text-[11px] font-medium text-gray-500 uppercase tracking-wide">Filière</label>
          <select
            className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 text-gray-800 bg-white focus:outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100 transition-all"
            value={filiere}
            onChange={(e) => { setFiliere(e.target.value); setClasse(''); setModule('') }}
          >
            <option value="">Sélectionner une filière…</option>
            {FILIERES.map(f => <option key={f} value={f}>{f}</option>)}
          </select>
        </div>

        <div className="flex flex-col gap-1">
          <label className="text-[11px] font-medium text-gray-500 uppercase tracking-wide">Classe</label>
          <select
            className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 text-gray-800 bg-white focus:outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
            value={classe}
            onChange={(e) => { setClasse(e.target.value); setModule('') }}
            disabled={!filiere}
          >
            <option value="">Sélectionner une classe…</option>
            {classes.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>

        <div className="flex flex-col gap-1">
          <label className="text-[11px] font-medium text-gray-500 uppercase tracking-wide">Module</label>
          <select
            className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 text-gray-800 bg-white focus:outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
            value={module}
            onChange={(e) => setModule(e.target.value)}
            disabled={!classe}
          >
            <option value="">Sélectionner un module…</option>
            {modules.map(m => <option key={m} value={m}>{m}</option>)}
          </select>
        </div>

        <div className="flex flex-col gap-1">
          <label className="text-[11px] font-medium text-gray-500 uppercase tracking-wide">Enseignant</label>
          <select
            className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 text-gray-800 bg-white focus:outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
            value={teacher}
            onChange={(e) => setTeacher(e.target.value)}
            disabled={!module}
          >
            <option value="">Sélectionner un enseignant…</option>
            {TEACHERS.map(t => <option key={t} value={t}>{t}</option>)}
          </select>
        </div>
      </div>

      <button
        className="w-full py-2 px-4 rounded-lg text-sm font-semibold bg-blue-500 text-white hover:bg-blue-600 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        disabled={!filiere || !classe || !module || !teacher}
        onClick={onClose}
      >
        Confirmer l'affectation
      </button>
    </div>
  )
}

// ─── Main App ─────────────────────────────────────────────────────────────────

export default function App() {
  const [selectedRoomId, setSelectedRoomId] = useState('amphi-a')
  const [screen, setScreen] = useState<AppScreen>('default')
  const [hoveredCell, setHoveredCell] = useState<string | null>(null)
  const [openPanel, setOpenPanel] = useState<{ slot: string; day: string } | null>(null)
  const panelAnchorRef = useRef<HTMLDivElement>(null)

  const room = selectedRoomId === 'salle-tp-12' && screen === 'empty'
    ? ROOMS.find(r => r.id === 'salle-tp-12')!
    : ROOMS.find(r => r.id === selectedRoomId)!

  const hasConflict = screen === 'default' && selectedRoomId === 'amphi-a'

  function handleRoomSelect(id: string) {
    setSelectedRoomId(id)
    setOpenPanel(null)
    if (id === 'salle-tp-12') setScreen('empty')
    else setScreen('default')
  }

  function handleCellClick(slotId: string, dayShort: string) {
    const cell = room.grid[slotId]?.[dayShort]
    if (!cell || cell.sessions.length === 0) {
      setOpenPanel({ slot: SLOTS.find(s => s.id === slotId)!.label, day: dayShort })
      setScreen('panel')
    }
  }

  function closePanel() {
    setOpenPanel(null)
    setScreen(selectedRoomId === 'salle-tp-12' ? 'empty' : 'default')
  }

  const screenTabs: { id: AppScreen; label: string }[] = [
    { id: 'default', label: 'État par défaut (conflit)' },
    { id: 'panel', label: 'Panneau d\'affectation' },
    { id: 'empty', label: 'Salle vide' },
  ]

  return (
    <div className="min-h-screen bg-gray-50 font-sans">
      {/* Screen switcher */}
      <div className="bg-white border-b border-gray-100 px-6 py-2 flex items-center gap-1">
        <span className="text-[11px] font-medium text-gray-400 uppercase tracking-wide mr-3">Écran :</span>
        {screenTabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => {
              setScreen(tab.id)
              if (tab.id === 'empty') setSelectedRoomId('salle-tp-12')
              else { setSelectedRoomId('amphi-a'); setOpenPanel(null) }
            }}
            className={`px-3 py-1 rounded-md text-xs font-medium transition-colors ${
              screen === tab.id
                ? 'bg-gray-800 text-white'
                : 'text-gray-500 hover:text-gray-700 hover:bg-gray-100'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Main content */}
      <div className="max-w-6xl mx-auto px-6 py-6 flex flex-col gap-4">

        {/* 1. Room selector */}
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-2 flex-wrap">
            {ROOMS.map((r) => (
              <button
                key={r.id}
                onClick={() => handleRoomSelect(r.id)}
                className={`px-3.5 py-1.5 rounded-lg text-sm font-medium border transition-all ${
                  selectedRoomId === r.id
                    ? 'bg-blue-50 border-blue-400 text-blue-700'
                    : 'bg-white border-gray-200 text-gray-600 hover:border-gray-300 hover:text-gray-800'
                }`}
              >
                {r.label}
              </button>
            ))}
          </div>
          <button className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-blue-500 text-white text-sm font-semibold hover:bg-blue-600 transition-colors flex-shrink-0">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 16 16">
              <path d="M8 3v10M3 8h10" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round"/>
            </svg>
            Nouvelle affectation
          </button>
        </div>

        {/* 2. Room header */}
        <div className="flex items-center justify-between bg-white border border-gray-200 rounded-xl px-5 py-3.5">
          <div>
            <span className="text-base font-bold text-gray-900">{room.label}</span>
            <span className="ml-2 text-sm text-gray-400">{room.building} · {room.capacity} places</span>
          </div>
          <div className="flex items-center gap-4">
            {([
              { type: 'CM' as CourseType, label: 'CM — Cours magistral' },
              { type: 'TD' as CourseType, label: 'TD — Travaux dirigés' },
              { type: 'TP' as CourseType, label: 'TP — Travaux pratiques' },
              { type: 'conflict' as CourseType, label: 'Conflit' },
            ]).map(({ type, label }) => (
              <div key={type} className="flex items-center gap-1.5">
                <span className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${typeStyles[type].dot}`} />
                <span className="text-xs text-gray-500">{label}</span>
              </div>
            ))}
          </div>
        </div>

        {/* 3. Conflict alert */}
        {hasConflict && <AlertBanner />}

        {/* 4. Weekly grid */}
        <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
          {/* Header row */}
          <div className="grid border-b border-gray-100" style={{ gridTemplateColumns: '88px repeat(6, 1fr)' }}>
            <div className="px-3 py-3 border-r border-gray-100" />
            {DAYS.map((d) => (
              <div key={d.short} className="px-3 py-3 border-r border-gray-100 last:border-r-0 text-center">
                <div className="text-xs font-semibold text-gray-700">{d.short}</div>
                <div className="text-[10px] text-gray-400 mt-0.5">{d.date}</div>
              </div>
            ))}
          </div>

          {/* Slot rows */}
          {SLOTS.map((slot, slotIdx) => (
            <div key={slot.id}>
              {/* Pause divider between slot1 and slot2 */}
              {slotIdx === 1 && (
                <div className="grid border-b border-gray-100" style={{ gridTemplateColumns: '88px repeat(6, 1fr)' }}>
                  <div className="px-3 py-1.5 border-r border-gray-100">
                    <span className="text-[9px] font-medium text-gray-300 uppercase tracking-widest">Pause</span>
                  </div>
                  {DAYS.map((d) => (
                    <div key={d.short} className="border-r border-gray-100 last:border-r-0 border-dashed py-1.5" />
                  ))}
                </div>
              )}

              <div
                className={`grid border-b border-gray-100 last:border-b-0`}
                style={{ gridTemplateColumns: '88px repeat(6, 1fr)', minHeight: '88px' }}
              >
                {/* Time label */}
                <div className="px-3 py-3 border-r border-gray-100 flex items-start pt-3">
                  <span className="text-[11px] font-medium text-gray-400 leading-tight">{slot.label}</span>
                </div>

                {/* Day cells */}
                {DAYS.map((d) => {
                  const cellKey = `${slot.id}-${d.short}`
                  const cell = screen === 'empty' ? { sessions: [] } : (room.grid[slot.id]?.[d.short] || { sessions: [] })
                  const isConflict = hasConflict && cell.sessions.length > 1
                  const isEmpty = cell.sessions.length === 0
                  const isPanelOpen = screen === 'panel' && openPanel?.slot === slot.label && openPanel?.day === d.short

                  return (
                    <div
                      key={d.short}
                      className="border-r border-gray-100 last:border-r-0 p-1.5 relative"
                      ref={isPanelOpen ? panelAnchorRef : undefined}
                    >
                      {isConflict ? (
                        <ConflictCell sessions={cell.sessions} />
                      ) : isEmpty ? (
                        <EmptyCell
                          onHover={(v) => setHoveredCell(v ? cellKey : null)}
                          isHovered={hoveredCell === cellKey}
                          onClick={() => handleCellClick(slot.id, d.short)}
                        />
                      ) : (
                        <SessionCell session={cell.sessions[0]} />
                      )}

                      {isPanelOpen && openPanel && (
                        <QuickPanel
                          slot={openPanel.slot}
                          day={openPanel.day}
                          anchorRef={panelAnchorRef}
                          onClose={closePanel}
                        />
                      )}
                    </div>
                  )
                })}
              </div>
            </div>
          ))}
        </div>

        {/* Footer note */}
        <div className="text-[11px] text-gray-400 text-center">
          Semaine du 11 au 16 août 2026 · Planification {room.label}
        </div>
      </div>
    </div>
  )
}
