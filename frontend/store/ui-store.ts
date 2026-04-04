import { create } from "zustand";

type UIState = {
  selectedCondition: string | null;
  setSelectedCondition: (slug: string) => void;
};

export const useUIStore = create<UIState>((set) => ({
  selectedCondition: "nf1",
  setSelectedCondition: (slug) => set({ selectedCondition: slug }),
}));
