import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type PropsWithChildren,
} from "react";
import { Button } from "./components";

export type Theme = "light" | "dark";

const CANONICAL_THEME_KEY = "quant-research-theme";
const LEGACY_THEME_KEYS = [
  "quant-dashboard-theme",
  "quant-calm-theme",
  "dram-price-theme",
  "etf-tracking-theme",
  "momentum-factor-theme",
  "sox-theme",
] as const;

interface ThemeContextValue {
  theme: Theme;
  setTheme: (theme: Theme) => void;
  toggleTheme: () => void;
}

const ThemeContext = createContext<ThemeContextValue | null>(null);

function isTheme(value: string | null): value is Theme {
  return value === "light" || value === "dark";
}

export function resolveInitialTheme(): Theme {
  if (typeof window === "undefined") {
    return "light";
  }

  const queryTheme = new URLSearchParams(window.location.search).get("theme");
  if (isTheme(queryTheme)) {
    return queryTheme;
  }

  try {
    const canonical = window.localStorage.getItem(CANONICAL_THEME_KEY);
    if (isTheme(canonical)) {
      return canonical;
    }
    for (const key of LEGACY_THEME_KEYS) {
      const legacy = window.localStorage.getItem(key);
      if (isTheme(legacy)) {
        window.localStorage.setItem(CANONICAL_THEME_KEY, legacy);
        return legacy;
      }
    }
  } catch {
    // A storage policy must not prevent the dashboard from rendering.
  }

  return window.matchMedia?.("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
}

export function ThemeProvider({ children }: PropsWithChildren) {
  const [theme, setTheme] = useState<Theme>(resolveInitialTheme);

  useEffect(() => {
    const root = document.documentElement;
    root.dataset.theme = theme;
    root.style.colorScheme = theme;
    try {
      window.localStorage.setItem(CANONICAL_THEME_KEY, theme);
    } catch {
      // Storage can be unavailable in privacy-restricted environments.
    }
  }, [theme]);

  const toggleTheme = useCallback(() => {
    setTheme((current) => (current === "light" ? "dark" : "light"));
  }, []);

  const value = useMemo(
    () => ({ theme, setTheme, toggleTheme }),
    [theme, toggleTheme],
  );
  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeContextValue {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error("useTheme must be used inside ThemeProvider.");
  }
  return context;
}

export function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();
  const nextLabel =
    theme === "light" ? "다크 모드로 전환" : "라이트 모드로 전환";

  return (
    <Button
      aria-label={nextLabel}
      aria-pressed={theme === "dark"}
      className="qr-theme-toggle"
      onClick={toggleTheme}
      size="icon"
      title={nextLabel}
      variant="ghost"
    >
      <span aria-hidden="true">{theme === "light" ? "☾" : "☀"}</span>
    </Button>
  );
}
