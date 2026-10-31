import "../client/validation-runtime";
import { z } from "zod";

// Projections only: actual responses also carry fields intentionally unsupported
// here. See api.py/templates.py/assets.py and synthetic FastAPI wire fixtures.
export const accessSchema = z.object({ can_edit: z.boolean() });
export const templatesSchema = z.array(z.object({
  template_id: z.string(), name: z.string(), description: z.string(),
  family: z.enum(["offer", "pilot", "marketing"]),
  source_type: z.enum(["trip", "campaign"]), layout_variants: z.array(z.string()),
  confidentiality: z.enum(["public", "client", "internal", "internal_restricted"]),
  default_sections: z.array(z.object({ role: z.string(), title: z.string(), binding: z.string(), required: z.boolean() })),
}));
export const assetSchema = z.object({ asset_id: z.string(), media_type: z.enum(["image/jpeg", "image/png", "image/webp"]) });
