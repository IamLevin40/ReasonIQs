let intervalId = null;
let lastTick = 0;

export function stopTimer() {
  if (intervalId !== null) clearInterval(intervalId);
  intervalId = null;
}

export function startTimer(onTick, onExpire) {
  stopTimer();
  lastTick = performance.now();
  intervalId = setInterval(() => {
    const now = performance.now();
    const elapsed = (now - lastTick) / 1000;
    lastTick = now;
    onTick(elapsed, onExpire);
  }, 200);
}
