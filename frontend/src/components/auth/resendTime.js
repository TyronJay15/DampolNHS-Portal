// When the next code may be requested, from a send response ({ resend_in } in seconds).
export function nextResendAt(response) {
  return Date.now() + (Number(response?.resend_in) || 60) * 1000;
}
