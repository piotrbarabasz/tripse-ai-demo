import { useEffect, useState } from "react";
import { Activity } from "lucide-react";
import { readHealth } from "./health";

type State = "loading" | "success" | "error" | "timeout";
export const HEALTH_TIMEOUT_MS = 5000;

export function HealthStatus() {
  const [state, setState] = useState<State>("loading");
  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    let timedOut = false;
    const timer = window.setTimeout(() => {
      timedOut = true;
      controller.abort();
      if (active) setState("timeout");
    }, HEALTH_TIMEOUT_MS);
    void readHealth(controller.signal)
      .then(() => {
        if (active && !timedOut) setState("success");
      })
      .catch(() => {
        if (active && !timedOut) setState("error");
      })
      .finally(() => window.clearTimeout(timer));
    return () => {
      active = false;
      window.clearTimeout(timer);
      controller.abort();
    };
  }, []);

  return (
    <section className="health-panel" aria-labelledby="health-title">
      <Activity size={20} aria-hidden="true" />
      <div>
        <h2 id="health-title">Połączenie z usługą</h2>
        <p role={state === "error" || state === "timeout" ? "alert" : "status"}>
          {state === "loading" && "Sprawdzanie połączenia…"}
          {state === "success" && "Usługa odpowiada prawidłowo."}
          {state === "error" &&
            "Nie udało się sprawdzić połączenia. Spróbuj ponownie po odświeżeniu strony."}
          {state === "timeout" &&
            "Przekroczono czas oczekiwania na usługę. Spróbuj ponownie po odświeżeniu strony."}
        </p>
        <p className="health-note">
          Ten test sprawdza dostępność usługi. Nie potwierdza zalogowania ani
          uprawnień.
        </p>
      </div>
    </section>
  );
}
