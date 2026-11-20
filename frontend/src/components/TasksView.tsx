import React, { useState, useEffect } from 'react';
import {
  Plus,
  CheckCircle2,
  Circle,
  Trash2,
  Clock,
} from 'lucide-react';

export interface TaskItem {
  id: string;
  title: string;
  completed: boolean;
  priority: 'high' | 'medium' | 'low';
  dueDate: string;
}

const DEFAULT_TASKS: TaskItem[] = [
  {
    id: 'task-1',
    title: 'Verify Faster-Whisper INT8 latency with multi-threading',
    completed: true,
    priority: 'high',
    dueDate: 'Today',
  },
  {
    id: 'task-2',
    title: 'Benchmark streaming Piper vs Edge-TTS output quality',
    completed: false,
    priority: 'high',
    dueDate: 'Today',
  },
  {
    id: 'task-3',
    title: 'Review Wikipedia image proxy allowlist headers',
    completed: false,
    priority: 'medium',
    dueDate: 'Tomorrow',
  },
  {
    id: 'task-4',
    title: 'Configure local Ollama memory retention parameters',
    completed: false,
    priority: 'low',
    dueDate: 'Nov 20',
  },
];

export const TasksView: React.FC = () => {
  const [tasks, setTasks] = useState<TaskItem[]>(() => {
    try {
      const saved = localStorage.getItem('aura_desktop_tasks');
      return saved ? JSON.parse(saved) : DEFAULT_TASKS;
    } catch {
      return DEFAULT_TASKS;
    }
  });

  const [filter, setFilter] = useState<'all' | 'pending' | 'completed'>('all');
  const [newTitle, setNewTitle] = useState('');
  const [newPriority, setNewPriority] = useState<'high' | 'medium' | 'low'>('medium');
  const [newDueDate, setNewDueDate] = useState('Today');

  useEffect(() => {
    try {
      localStorage.setItem('aura_desktop_tasks', JSON.stringify(tasks));
    } catch {}
  }, [tasks]);

  const handleToggleTask = (id: string) => {
    setTasks((prev) =>
      prev.map((t) => (t.id === id ? { ...t, completed: !t.completed } : t))
    );
  };

  const handleDeleteTask = (id: string) => {
    setTasks((prev) => prev.filter((t) => t.id !== id));
  };

  const handleAddTask = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim()) return;

    const newTask: TaskItem = {
      id: `task-${Date.now()}`,
      title: newTitle.trim(),
      completed: false,
      priority: newPriority,
      dueDate: newDueDate || 'Today',
    };

    setTasks([newTask, ...tasks]);
    setNewTitle('');
  };

  const filteredTasks = tasks.filter((t) => {
    if (filter === 'pending') return !t.completed;
    if (filter === 'completed') return t.completed;
    return true;
  });

  const getPriorityBadge = (p: TaskItem['priority']) => {
    switch (p) {
      case 'high':
        return <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-rose-50 text-rose-700 border border-rose-200">High</span>;
      case 'medium':
        return <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-amber-50 text-amber-700 border border-amber-200">Medium</span>;
      case 'low':
      default:
        return <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">Low</span>;
    }
  };

  const pendingCount = tasks.filter((t) => !t.completed).length;

  return (
    <div className="flex-1 w-full max-w-3xl mx-auto flex flex-col h-full py-6 px-4 animate-in fade-in duration-200 select-none">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-[var(--border)] pb-4 mb-4">
        <div>
          <h2 className="text-xl font-semibold text-[var(--text-primary)]">Tasks & Reminders</h2>
          <p className="text-xs text-[var(--text-secondary)] mt-0.5">
            {pendingCount} pending task{pendingCount === 1 ? '' : 's'} · Local-first task manager
          </p>
        </div>

        {/* Filter Pills */}
        <div className="flex items-center gap-1 p-1 rounded-xl bg-[var(--surface-primary)] border border-[var(--border)] text-xs font-medium">
          <button
            type="button"
            onClick={() => setFilter('all')}
            className={`px-3 py-1 rounded-lg transition cursor-pointer ${
              filter === 'all'
                ? 'bg-[var(--surface-secondary)] text-[var(--text-primary)] font-semibold shadow-2xs'
                : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
            }`}
          >
            All ({tasks.length})
          </button>
          <button
            type="button"
            onClick={() => setFilter('pending')}
            className={`px-3 py-1 rounded-lg transition cursor-pointer ${
              filter === 'pending'
                ? 'bg-[var(--surface-secondary)] text-[var(--text-primary)] font-semibold shadow-2xs'
                : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
            }`}
          >
            Pending ({pendingCount})
          </button>
          <button
            type="button"
            onClick={() => setFilter('completed')}
            className={`px-3 py-1 rounded-lg transition cursor-pointer ${
              filter === 'completed'
                ? 'bg-[var(--surface-secondary)] text-[var(--text-primary)] font-semibold shadow-2xs'
                : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
            }`}
          >
            Completed ({tasks.length - pendingCount})
          </button>
        </div>
      </div>

      {/* Add Task Form */}
      <form onSubmit={handleAddTask} className="w-full mb-5 flex flex-col sm:flex-row items-center gap-2 p-2 bg-[var(--surface-primary)] rounded-2xl border border-[var(--border)] shadow-2xs">
        <input
          type="text"
          value={newTitle}
          onChange={(e) => setNewTitle(e.target.value)}
          placeholder="Add a new task or reminder..."
          className="flex-1 bg-transparent px-3 py-1.5 text-xs text-[var(--text-primary)] placeholder-[var(--text-tertiary)] focus:outline-none"
        />

        <div className="flex items-center gap-2 w-full sm:w-auto justify-end px-2">
          {/* Priority selector */}
          <select
            value={newPriority}
            onChange={(e) => setNewPriority(e.target.value as any)}
            className="text-xs bg-[var(--surface-secondary)] text-[var(--text-primary)] px-2 py-1 rounded-lg border border-[var(--border)] focus:outline-none cursor-pointer"
          >
            <option value="low">Low Priority</option>
            <option value="medium">Medium Priority</option>
            <option value="high">High Priority</option>
          </select>

          {/* Due date picker or quick options */}
          <input
            type="text"
            value={newDueDate}
            onChange={(e) => setNewDueDate(e.target.value)}
            placeholder="Due date (e.g. Today)"
            className="w-24 text-xs bg-[var(--surface-secondary)] text-[var(--text-primary)] px-2 py-1 rounded-lg border border-[var(--border)] focus:outline-none"
          />

          <button
            type="submit"
            disabled={!newTitle.trim()}
            className="px-3.5 py-1.5 rounded-xl bg-[var(--text-primary)] hover:bg-black text-[var(--surface-primary)] text-xs font-semibold flex items-center gap-1 transition disabled:opacity-30 cursor-pointer"
          >
            <Plus size={14} />
            <span>Add</span>
          </button>
        </div>
      </form>

      {/* Tasks List */}
      <div className="flex-1 overflow-y-auto aura-scroller flex flex-col gap-2">
        {filteredTasks.length === 0 ? (
          <div className="flex-1 flex flex-col items-center justify-center text-[var(--text-tertiary)] text-xs py-12">
            <CheckCircle2 size={36} className="mb-2 opacity-40 text-emerald-500" />
            <span>No tasks matching this view. You're all caught up!</span>
          </div>
        ) : (
          filteredTasks.map((task) => (
            <div
              key={task.id}
              onClick={() => handleToggleTask(task.id)}
              className={`p-3.5 rounded-2xl border transition flex items-center justify-between cursor-pointer group ${
                task.completed
                  ? 'bg-[var(--surface-primary)]/50 border-[var(--border)] opacity-65'
                  : 'bg-[var(--surface-primary)] border-[var(--border)] hover:border-[var(--border-strong)] shadow-2xs'
              }`}
            >
              <div className="flex items-center gap-3 min-w-0">
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleToggleTask(task.id);
                  }}
                  className="text-[var(--text-tertiary)] hover:text-[var(--accent)] transition"
                >
                  {task.completed ? (
                    <CheckCircle2 size={18} className="text-emerald-500" />
                  ) : (
                    <Circle size={18} />
                  )}
                </button>

                <div className="flex flex-col min-w-0">
                  <span
                    className={`text-xs font-medium text-[var(--text-primary)] truncate ${
                      task.completed ? 'line-through text-[var(--text-tertiary)]' : ''
                    }`}
                  >
                    {task.title}
                  </span>
                  <div className="flex items-center gap-2 mt-0.5 text-[10px] text-[var(--text-tertiary)]">
                    <span className="flex items-center gap-1">
                      <Clock size={10} />
                      {task.dueDate}
                    </span>
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-2 shrink-0">
                {getPriorityBadge(task.priority)}

                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDeleteTask(task.id);
                  }}
                  title="Delete task"
                  className="opacity-0 group-hover:opacity-100 p-1 rounded-md text-[var(--text-tertiary)] hover:text-rose-600 transition"
                >
                  <Trash2 size={13} />
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
