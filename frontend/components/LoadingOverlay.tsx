interface Props { msg: string }

export default function LoadingOverlay({ msg }: Props) {
  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(2,3,24,0.92)',
      display: 'flex', flexDirection: 'column', alignItems: 'center',
      justifyContent: 'center', gap: '1.5rem', zIndex: 999,
      backdropFilter: 'blur(4px)'
    }}>
      <div style={{
        width: 52, height: 52,
        border: '4px solid rgba(255,215,0,0.2)',
        borderTopColor: 'var(--gold)',
        borderRadius: '50%',
        animation: 'spin 0.8s linear infinite'
      }} />
      <p style={{
        color: 'var(--gold)',
        fontFamily: "'Bebas Neue', sans-serif",
        fontSize: '1.35rem',
        letterSpacing: '2px'
      }}>{msg}</p>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  )
}