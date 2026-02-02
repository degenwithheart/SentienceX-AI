import { apiGet } from "./api";

export async function hasProfile() {
  try {
    const res = await apiGet("/user/profile");
    return !!(res && res.exists);
  } catch {
    return true; // don't hard-block if API is unreachable
  }
}

