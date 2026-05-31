import { createContext, useContext, useState, useCallback, useRef } from 'react'

const ToastContext = createContext(null)

export function ToastProvider({ children }) {
  const [toast, setToast] = useState({ msg: '', type: '', visible: false })
  const timerRef = useRef(null)

  const showToast = useCallback((msg, type = '') => {
    clearTimeout(timerRef.current)
    setToast({ msg, type, visible: true })
    timerRef.current = setTimeout(() => setToast(t => ({ ...t, visible: false })), 2800)
  }, [])

  return (
    <ToastContext.Provider value={showToast}>
      {children}
      <div className={`toast${toast.visible ? ' show' : ''} ${toast.type}`}>
        {toast.msg}
      </div>
    </ToastContext.Provider>
  )
}

export const useToast = () => useContext(ToastContext)
