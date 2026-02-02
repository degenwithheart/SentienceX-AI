import { toast } from "sonner";

export function notifyError(err, fallback = "Something went wrong") {
  const msg =
    (err && (err.message || err.toString && err.toString())) || fallback;
  toast.error(msg);
}

export function notifyOk(message) {
  toast.success(message);
}

export function notifyInfo(message) {
  toast(message);
}

