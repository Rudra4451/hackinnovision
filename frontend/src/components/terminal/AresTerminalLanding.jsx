import React, { useState, useEffect } from 'react';
import AresLogo from './AresLogo';

/**
 * A.R.E.S. Entry Terminal / Mission Dossier Landing Page
 * Stark classified government aerospace terminal.
 * Matte black #121212, hairline borders #333333, tabular monospace,
 * strict textual mission dossier with terminal typewriter effect,
 * and harsh rectangular call-to-action button [ INITIATE MISSION CONTROL ].
 */
export default function AresTerminalLanding({ onInitiate }) {
  const [typedLines, setTypedLines] = useState([]);
  const [isTypingComplete, setIsTypingComplete] = useState(false);

  const dossierLines = [
    'AUTHENTICATING TERMINAL SESSION... [SEC-LEVEL 4 GRANTED]',
    'SECTOR: JEZERO CRATER QUADRANGLE // LAT: 18.38°N LON: 77.58°E',
    'AI4MARS RECONNAISSANCE ENGINE ONLINE: SOIL / BEDROCK / SAND / BOULDER',
    'KINEMATIC TURN-PENALTY A* KERNEL ARMED (HEADING-AWARE G-COST)',
    'DYNAMIC HAZARD SENSING: ACTIVE IN-SITU MID-COURSE REROUTING',
    'TRAJECTORY SMOOTHING: CONTINUOUS GRADIENT DESCENT ENABLED',
    'ALL AUTONOMOUS SYSTEMS NOMINAL. READY FOR MISSION DISPATCH.',
  ];

  useEffect(() => {
    let currentLine = 0;
    const interval = setInterval(() => {
      if (currentLine < dossierLines.length) {
        setTypedLines((prev) => [...prev, dossierLines[currentLine]]);
        currentLine++;
      } else {
        setIsTypingComplete(true);
        clearInterval(interval);
      }
    }, 180);

    return () => clearInterval(interval);
  }, []);

  return (
    <div
      className="fixed inset-0 w-screen h-screen bg-[#121212] text-[#D4D4D4] font-mono flex items-center justify-center p-4 select-none z-[9999]"
      style={{
        backgroundColor: '#121212',
        color: '#D4D4D4',
        fontFamily: "'JetBrains Mono', 'IBM Plex Mono', monospace",
      }}
    >
      {/* Stark Hairline Centered Fixed-Width Dossier Box */}
      <div
        className="w-full max-w-[680px] bg-[#121212] border border-[#333333] p-8 rounded-none relative"
        style={{
          backgroundColor: '#121212',
          borderColor: '#333333',
          borderWidth: '1px',
          borderStyle: 'solid',
        }}
      >
        {/* Classification Header Banner */}
        <div className="flex justify-between items-center border-b border-[#333333] pb-3 mb-6 text-[10px] text-[#858585] tracking-widest">
          <span>CLASSIFICATION: RESTRICTED // MIL-SPEC-MARS-09</span>
          <span className="text-[#DC2626] font-bold">[ SEC_CLEARANCE_LVL_4 ]</span>
        </div>

        {/* Top Center Geometric Logo */}
        <div className="flex flex-col items-center justify-center mb-6">
          <AresLogo size={64} showText={false} />
          <h1
            className="text-lg font-bold tracking-[0.2em] text-[#D4D4D4] mt-3 uppercase"
            style={{ fontFamily: "'JetBrains Mono', monospace" }}
          >
            SYSTEM: A.R.E.S. MARS-09
          </h1>
          <h2 className="text-xs text-[#858585] tracking-[0.14em] uppercase mt-1">
            AUTONOMOUS SURFACE NAVIGATION KERNEL
          </h2>
        </div>

        {/* Dossier Metadata Grid */}
        <div className="grid grid-cols-2 gap-2 border border-[#333333] p-3 text-[11px] mb-5 bg-[#161616]">
          <div>
            <span className="text-[#858585]">PROJECT:</span>{' '}
            <span className="text-[#D4D4D4] font-semibold">A.R.E.S. (ROVER-09)</span>
          </div>
          <div>
            <span className="text-[#858585]">ARCHITECTURE:</span>{' '}
            <span className="text-[#0284C7] font-semibold">A* KINEMATIC MATRIX</span>
          </div>
          <div>
            <span className="text-[#858585]">PERCEPTION:</span>{' '}
            <span className="text-[#D4D4D4] font-semibold">AI4MARS 4-CLASS SEMANTIC</span>
          </div>
          <div>
            <span className="text-[#858585]">STATUS:</span>{' '}
            <span className="text-[#0284C7] font-semibold">STANDBY FOR DISPATCH</span>
          </div>
        </div>

        {/* Textual Mission Objectives Dossier */}
        <div className="border border-[#333333] p-4 mb-6 bg-[#141414] min-h-[160px]">
          <div className="text-[10px] text-[#858585] border-b border-[#333333] pb-1 mb-2 tracking-wider">
            MISSION DIRECTIVES & CORE SUBSYSTEMS:
          </div>
          <ul className="space-y-1.5 text-xs text-[#D4D4D4]">
            {typedLines.map((line, idx) => (
              <li key={idx} className="flex items-start gap-2">
                <span className="text-[#DC2626] font-bold select-none">&gt;</span>
                <span className="tabular-nums">{line}</span>
              </li>
            ))}
            {!isTypingComplete && (
              <li className="flex items-center gap-1 text-[#858585] text-xs">
                <span className="text-[#DC2626]">&gt;</span>
                <span className="inline-block w-2 h-3.5 bg-[#D4D4D4] animate-pulse" />
              </li>
            )}
          </ul>
        </div>

        {/* Harsh Rectangular Call to Action Button */}
        <div className="flex flex-col items-center gap-3">
          <button
            onClick={onInitiate}
            className="w-full py-3.5 px-6 bg-[#121212] text-[#D4D4D4] border border-[#333333] rounded-none font-mono text-sm font-bold tracking-[0.18em] uppercase cursor-pointer hover:bg-[#D4D4D4] hover:text-[#121212] active:bg-[#DC2626] active:text-[#FFFFFF] active:border-[#DC2626] transition-none flex items-center justify-center gap-2"
            style={{
              backgroundColor: '#121212',
              borderColor: '#333333',
              borderRadius: '0px',
            }}
          >
            <span>[ INITIATE MISSION CONTROL ]</span>
          </button>

          <div className="flex justify-between w-full text-[9px] text-[#858585] mt-1">
            <span>TERMINAL ID: T-7718-ARES</span>
            <span>ENCRYPTION: AES-256-MIL</span>
            <span>KERNEL: ACTIVE</span>
          </div>
        </div>
      </div>
    </div>
  );
}
