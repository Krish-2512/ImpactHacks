import { create } from 'zustand'

export const useAgentStore = create((set) => ({
  latestReport: null,
  isRunning: false,
  cycleId: null,
  setReport: (report) => set({ latestReport: report }),
  setRunning: (val, cycleId = null) => set({ isRunning: val, cycleId }),
}))
