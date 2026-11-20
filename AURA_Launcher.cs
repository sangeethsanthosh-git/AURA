using System;
using System.Diagnostics;
using System.IO;
using System.Net.Sockets;
using System.Threading;
using System.Windows.Forms;

namespace AuraLauncher
{
    static class Program
    {
        [STAThread]
        static void Main(string[] args)
        {
            try
            {
                Application.EnableVisualStyles();
                Application.SetCompatibleTextRenderingDefault(false);

                string baseDir = AppDomain.CurrentDomain.BaseDirectory.TrimEnd('\\', '/');

                // 1. Terminate orphaned / hung electron background processes
                try
                {
                    foreach (var proc in Process.GetProcessesByName("electron"))
                    {
                        try { proc.Kill(); } catch { }
                    }
                }
                catch { }

                // 2. Ensure Ollama AI Engine is running
                if (!IsPortOpen("127.0.0.1", 11434, 400))
                {
                    string localAppData = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
                    string programFiles = Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles);
                    string[] ollamaCandidates = new string[]
                    {
                        Path.Combine(localAppData, "Programs", "Ollama", "ollama.exe"),
                        Path.Combine(programFiles, "Ollama", "ollama.exe")
                    };

                    bool launchedOllama = false;
                    foreach (var ollamaExe in ollamaCandidates)
                    {
                        if (File.Exists(ollamaExe))
                        {
                            try
                            {
                                var psi = new ProcessStartInfo(ollamaExe, "serve")
                                {
                                    CreateNoWindow = true,
                                    UseShellExecute = false,
                                    WindowStyle = ProcessWindowStyle.Hidden
                                };
                                Process.Start(psi);
                                launchedOllama = true;
                                break;
                            }
                            catch { }
                        }
                    }

                    if (!launchedOllama)
                    {
                        try
                        {
                            var psi = new ProcessStartInfo("ollama", "serve")
                            {
                                CreateNoWindow = true,
                                UseShellExecute = false,
                                WindowStyle = ProcessWindowStyle.Hidden
                            };
                            Process.Start(psi);
                        }
                        catch { }
                    }
                }

                // 3. Ensure FastAPI Backend Service is running
                if (!IsPortOpen("127.0.0.1", 8000, 500))
                {
                    string[] pythonCandidates = new string[]
                    {
                        Path.Combine(baseDir, ".venv", "Scripts", "python.exe"),
                        Path.Combine(baseDir, "venv", "Scripts", "python.exe"),
                        Path.Combine(baseDir, "backend", ".venv", "Scripts", "python.exe")
                    };

                    string pythonExe = null;
                    foreach (var candidate in pythonCandidates)
                    {
                        if (File.Exists(candidate))
                        {
                            pythonExe = candidate;
                            break;
                        }
                    }

                    if (pythonExe != null)
                    {
                        var psi = new ProcessStartInfo(pythonExe, "-m uvicorn backend.api.app:app --host 127.0.0.1 --port 8000")
                        {
                            WorkingDirectory = baseDir,
                            CreateNoWindow = true,
                            UseShellExecute = false,
                            WindowStyle = ProcessWindowStyle.Hidden
                        };
                        Process.Start(psi);
                    }
                    else
                    {
                        string setupBat = Path.Combine(baseDir, "setup.bat");
                        if (File.Exists(setupBat))
                        {
                            var dialogResult = MessageBox.Show(
                                "AURA Python virtual environment was not found.\n\nWould you like to run 'setup.bat' now to configure the environment?",
                                "AURA Desktop Assistant",
                                MessageBoxButtons.YesNo,
                                MessageBoxIcon.Question
                            );
                            if (dialogResult == DialogResult.Yes)
                            {
                                Process.Start(new ProcessStartInfo(setupBat) { WorkingDirectory = baseDir });
                                return;
                            }
                        }
                    }
                }

                // Brief pause to allow ports to bind
                for (int i = 0; i < 10; i++)
                {
                    if (IsPortOpen("127.0.0.1", 8000, 300)) break;
                    Thread.Sleep(300);
                }

                // 4. Launch Desktop Window with explicit Normal Window Visibility (SW_SHOWNORMAL)
                string unpackedExe = Path.Combine(baseDir, "frontend", "dist-electron", "win-unpacked", "AURA.exe");
                string arguments = string.Join(" ", args);

                if (File.Exists(unpackedExe))
                {
                    var desktopPsi = new ProcessStartInfo(unpackedExe, arguments)
                    {
                        WorkingDirectory = Path.GetDirectoryName(unpackedExe),
                        WindowStyle = ProcessWindowStyle.Normal,
                        UseShellExecute = true
                    };
                    Process.Start(desktopPsi);
                }
                else
                {
                    string electronDist = Path.Combine(baseDir, "frontend", "node_modules", "electron", "dist", "electron.exe");
                    string mainCjs = Path.Combine(baseDir, "frontend", "electron", "main.cjs");

                    if (File.Exists(electronDist) && File.Exists(mainCjs))
                    {
                        var desktopPsi = new ProcessStartInfo(electronDist, "\"" + mainCjs + "\" " + arguments)
                        {
                            WorkingDirectory = Path.Combine(baseDir, "frontend"),
                            WindowStyle = ProcessWindowStyle.Normal,
                            UseShellExecute = true
                        };
                        Process.Start(desktopPsi);
                    }
                    else
                    {
                        string setupBat = Path.Combine(baseDir, "setup.bat");
                        MessageBox.Show(
                            "AURA Desktop UI components have not been built yet.\n\nPlease run 'setup.bat' to install dependencies and compile the desktop app.",
                            "AURA Desktop Assistant",
                            MessageBoxButtons.OK,
                            MessageBoxIcon.Information
                        );
                    }
                }
            }
            catch (Exception ex)
            {
                MessageBox.Show(
                    "AURA failed to initialize:\n\n" + ex.Message,
                    "AURA Desktop Assistant",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Error
                );
            }
        }

        static bool IsPortOpen(string host, int port, int timeoutMs)
        {
            try
            {
                using (var tcp = new TcpClient())
                {
                    var ar = tcp.BeginConnect(host, port, null, null);
                    bool success = ar.AsyncWaitHandle.WaitOne(timeoutMs);
                    if (!success) return false;
                    tcp.EndConnect(ar);
                    return true;
                }
            }
            catch
            {
                return false;
            }
        }
    }
}
