import { useEffect, useRef } from 'react';
import { useChatStore } from '../stores/chatStore';

interface ScheduledTask {
  id: string;
  text: string;
  executeAt: number;
}

let tasks: ScheduledTask[] = [];

export function getScheduledTasks() { return [...tasks]; }
export function clearScheduledTasks() { tasks = []; }
export function addScheduledTask(text: string, delayMs: number) {
  tasks.push({ id: Date.now().toString(), text, executeAt: Date.now() + delayMs });
}

export function useScheduler() {
  const intervalRef = useRef<ReturnType<typeof setInterval>>();
  useEffect(() => {
    intervalRef.current = setInterval(async () => {
      const now = Date.now();
      const due = tasks.filter(t => t.executeAt <= now);
      if (due.length === 0) return;
      tasks = tasks.filter(t => t.executeAt > now);
      const { host, token } = useChatStore.getState();
      if (!host || !token) return;
      for (const t of due) {
        try {
          await fetch(`${host}/api/send`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
            body: JSON.stringify({ text: t.text }),
          });
          useChatStore.getState().addMessage({
            id: `sched-${t.id}`, type: 'system', text: `⏰ 定时发送: ${t.text}`, timestamp: Date.now(),
          });
        } catch {}
      }
    }, 1000);
    return () => clearInterval(intervalRef.current);
  }, []);
}
