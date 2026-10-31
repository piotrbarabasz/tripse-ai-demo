import { z } from "zod";

// Must execute before schema construction. Even a caught new Function probe
// emits a violation under the app's strict script-src CSP.
z.config({ jitless: true });
