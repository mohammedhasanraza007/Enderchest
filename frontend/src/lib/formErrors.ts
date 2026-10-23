import { ApiError } from "../api/client";

// How a form shows a server refusal (PAGES.md 2, failure kind F-024): a problem on a field the
// form shows goes under that field; anything else (a field the form does not show, a conflict,
// a lost connection) becomes one general message, so nothing is ever swallowed.

export interface FormProblems {
  fields: Record<string, string>;
  general: string | null;
}

export function splitProblems(error: unknown, shownFields: readonly string[]): FormProblems {
  if (!(error instanceof ApiError)) {
    return { fields: {}, general: "Something went wrong. Nothing was lost." };
  }
  const fields: Record<string, string> = {};
  const unshown: string[] = [];
  const problems = error.details["problems"];
  if (error.code === "validation_error" && Array.isArray(problems)) {
    for (const item of problems as Array<{ field?: string; problem?: string }>) {
      // "attributes.size" belongs to the "attributes" field.
      const field = (item.field ?? "").split(".")[0] ?? "";
      if (shownFields.includes(field) && item.problem && fields[field] === undefined) {
        fields[field] = item.problem;
      } else if (item.problem) {
        unshown.push(item.problem);
      }
    }
    return { fields, general: unshown.length > 0 ? unshown.join(" ") : null };
  }
  const field = error.details["field"];
  if (typeof field === "string" && shownFields.includes(field)) {
    return { fields: { [field]: error.message }, general: null };
  }
  return { fields: {}, general: error.message };
}
