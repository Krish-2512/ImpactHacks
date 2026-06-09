import { useAutoTranslate } from '../hooks/useAutoTranslate'

/**
 * Mounts invisibly inside BrowserRouter to run the auto-translate hook.
 * Returns null — only exists to activate the hook globally.
 */
export default function AppInit() {
  useAutoTranslate()
  return null
}
