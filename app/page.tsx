"use client"
// Need "use client" only if you want this component to use react state. Otherwise, put state logic in child components and mark them "use client".

import Image from "next/image";
import { useEffect, useState } from "react";
import { listen } from '@tauri-apps/api/event';
import { invoke } from '@tauri-apps/api/core'; 
// import { Command } from '@tauri-apps/api/shell'
// import { appWindow } from '@tauri-apps/api/window'

// When using the Tauri global script (if not using the npm package)
// Be sure to set `app.withGlobalTauri` in `tauri.conf.json` to true
//
// const invoke = window.__TAURI__.core.invoke;
// declare global {
//   interface Window { __TAURI__: any; }
// }

export default function Home() {
  const docs_url = "https://github.com/dieharders/example-tauri-v2-python-server-sidecar";
  const DOMAIN = "localhost";
  const PORT = "8008";
  const [status, setStatus] = useState({ connected: false, info: "" });
  const [logs, setLogs] = useState("[ui] Listening for sidecar & network logs...");
  const connectButtonStyle = status.connected ? "hover:border-yellow-300 hover:bg-yellow-100 hover:dark:border-yellow-400 hover:dark:bg-yellow-500/50 border-dashed" : "hover:border-gray-300 hover:bg-gray-100 hover:dark:border-blue-400 hover:dark:bg-blue-500/50";
  const bgStyle = "bg-[url('/background.svg')] bg-cover bg-fixed bg-center bg-zinc-950";
  const buttonStyle = "group rounded-lg border border-transparent hover:backdrop-blur px-5 py-4 transition-colors text-left";
  const greyHoverStyle = "hover:border-gray-300 hover:bg-gray-100 hover:dark:border-neutral-700 hover:dark:bg-neutral-800/30";
  const descrStyle = "group-hover:opacity-100";
  const [message, setMessage] = useState("");


    


  const initSidecarListeners = async () => {
    // Listen for stdout lines from the sidecar
    const unlistenStdout = await listen('sidecar-stdout', (event) => {
      console.log('Sidecar stdout:', event.payload);
      if (`${event.payload}`.length > 0 && event.payload !== "\r\n")
        setLogs(prev => prev += `\n${event.payload}`)
    });

    // Listen for stderr lines from the sidecar
    const unlistenStderr = await listen('sidecar-stderr', (event) => {
      console.error('Sidecar stderr:', event.payload);
      if (`${event.payload}`.length > 0 && event.payload !== "\r\n")
        setLogs(prev => prev += `\n${event.payload}`)
    });

    // Cleanup listeners when not needed
    return () => {
      unlistenStdout();
      unlistenStderr();
    };
  }

  const apiAction = async (endpoint: string, method: string = 'GET', payload?: any) => {
    const url = `http://${DOMAIN}:${PORT}/${endpoint}`;
    try {
      const body = payload ? JSON.stringify(payload) : null;
      const headers = {
        "Content-Type": "application/json",
      };

      const res = await fetch(url, { method, headers, body });
      if (!res.ok) {
        throw new Error(`Response status: ${res.status}`);
      }
      const json = await res.json();
      console.log(json);
      // Success
      if (json?.message) {
        setLogs(prev => prev += `\n[server-response] ${json.message}`);
      }
      return json;
    } catch (err) {
      console.error(`[server-response] ${err}`);
      setLogs(prev => prev += `\n[server-response] ${err}`);
    }
  }

  const connectServerAction = async () => {
    try {
      const result = await apiAction("v1/connect");
      if (result) {
        setStatus({
          connected: true,
          info: `Host: ${result.data.host}\nProcess id: ${result.data.pid}\nDocs: ${result.data.host}/docs`,
        });
      }
      return;
    } catch (err) {
      console.error(`[ui] Failed to connect to api server. ${err}`);
    }
  }

  const shutdownSidecarAction = async () => {
    try {
      const result = await invoke("shutdown_sidecar");
      if (result) setStatus({
        connected: false,
        info: "",
      });
      return;
    } catch (err) {
      console.error(`[ui] Failed to shutdown sidecar. ${err}`);
    }
  }

  const startSidecarAction = async () => {
    try {
      await invoke("start_sidecar");
      return;
    } catch (err) {
      console.error(`[ui] Failed to start sidecar. ${err}`);
    }
  }

  const mockAPIAction = async () => {
    try {
      await apiAction("v1/completions", "POST", { prompt: "An example query." });
      return;
    } catch (err) {
      console.error(`[ui] Failed to get llm completion. ${err}`);
    }
  }

  // Start listening for server logs
  useEffect(() => {
    initSidecarListeners()
  }, [])

  // Listen for user key inputs and set full screen.
  useEffect(() => {
    const listener = (event: any) => {
      if (event.key === 'F11') {
        event.preventDefault(); // Prevent browser default behavior
        invoke('toggle_fullscreen');
      }
    }
    window.addEventListener('keydown', listener);
    // Cleanup
    return () => {
      window.removeEventListener('keydown', listener);
    }
  }, [])

  const startTaskAction = async () => {
    try {
      const result = await apiAction("start_task", "POST", { message });
      if (result) {
        setLogs(prev => prev += `\n[ui] Task started with message: ${message}`);
        setMessage(""); // Clear input after sending
      }
      return result;
    } catch (err) {
      console.error(`[ui] Failed to start task. ${err}`);
      setLogs(prev => prev += `\n[ui] Failed to start task: ${err}`);
    }
  }

  const handleSubmit = (e) => {
    e.preventDefault();
    if (message.trim()) {
      startTaskAction();
    }
  };  

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };


  // Start python api server. @TODO Update this for v2
  // This does the same shutdown procedure as in main.rs.
  // useEffect(() => {
  //   const start = async () => {
  //     // const { Command } = window.__TAURI__.shell;
  //     const command = Command.sidecar("bin/api/main");
  //     const { stdout, stderr } = await command.execute();
  //     console.log('stdout:', stdout, stderr);
  //     await appWindow.onCloseRequested(async (event) => {
  //       console.log('onCloseRequested', event);
  //       // shutdown the api server
  //       // shutdownSidecarAction()
  //       return
  //     })
  //     return;
  //   }
  //   start()
  // }, [])

  return (
    // <main classNameNameName={`relative flex min-h-screen flex-col items-center justify-between p-24 overflow-hidden ${bgStyle}`}>
    //   {/* Spinning Background */}
    //   <div classNameNameName={`absolute flex justify-center items-center left-[50%] right-[50%] bottom-[50%] top-[50%] w-[0px] h-[0px]`}>
    //     <div classNameNameName={`relative w-[100vw] h-[100vw] ${bgStyle} aspect-square animate-[spin_025s_linear_infinite]`}></div>
    //   </div>
    //   {/* Header/Footer */}
    //   <div classNameNameName="z-20 w-full max-w-5xl items-center justify-between font-mono text-sm lg:flex">
    //     {/* About */}
    //     <div classNameNameName="fixed left-0 top-0 flex flex-col items-center lg:items-start w-full justify-center border-b border-gray-300 bg-gradient-to-b from-zinc-200 pb-6 pt-8 backdrop-blur-2xl dark:border-neutral-800 dark:bg-zinc-800/30 dark:from-inherit lg:static lg:w-auto  lg:rounded-xl lg:border lg:bg-gray-200 lg:p-4 lg:dark:bg-zinc-800/30">
    //       <p>
    //         Get started by editing&nbsp;
    //         <code classNameNameName="font-mono font-bold text-yellow-300">src/backends/main.py</code>
    //       </p>
    //       <a href={docs_url}
    //         target="_blank"
    //         rel="noopener noreferrer"
    //       >
    //         Read the project docs:&nbsp;
    //         <code classNameNameName="font-mono font-bold text-yellow-300">here</code>
    //       </a>
    //     </div>
    //     {/* Title and Logo */}
    //     <div classNameNameName="fixed bottom-0 left-0 flex h-48 w-full items-end justify-center bg-gradient-to-t from-white via-white dark:from-black dark:via-black lg:static lg:h-auto lg:w-auto lg:bg-none pointer-events-none">
    //       <div
    //         classNameNameName="flex place-items-center gap-2 p-8 lg:p-0"
    //       >
    //         <div>
    //           <a classNameNameName="pointer-events-auto" href="https://sorob.net" target="_blank" rel="noopener noreferrer">
    //             tauri python sidecar
    //             <br></br>
    //             by @DIEHARDERS
    //           </a>
    //           <br></br>
    //           <a classNameNameName="pointer-events-auto" href="https://www.svgbackgrounds.com" target="_blank" rel="noopener noreferrer">
    //             BG by svgbackgrounds.com
    //           </a>
    //         </div>
    //         <Image
    //           src="/logo.svg"
    //           alt="App Logo"
    //           classNameNameName="dark"
    //           width={64}
    //           height={64}
    //           priority
    //         />
    //       </div>
    //     </div>
    //   </div>

    //   {/* Area displaying logs from server */}
    //   <code classNameNameName="relative flex max-w-[1200px] max-h-96 font-mono font-bold border dark:border-neutral-800 border-gray-300 rounded-lg backdrop-blur-2xl dark:bg-zinc-800/30 bg-neutral-400/30 p-4 mt-4 mb-4 whitespace-pre-wrap overflow-y-auto">{logs}</code>

    //   <div classNameNameName="z-10 mb-32 grid lg:mb-0 lg:grid-cols-4 items-start">
    //     {/* Connect to server button */}
    //     <button
    //       classNameNameName={`${buttonStyle} ${connectButtonStyle}`}
    //       disabled={status.connected}
    //       onClick={connectServerAction}
    //     >
    //       <h2 classNameNameName={`mb-3 text-2xl font-semibold`}>
    //         {status.connected ? "Connected " : "Connect to host"}
    //         <span classNameNameName="inline-block transition-transform group-hover:translate-x-1 motion-reduce:transform-none">
    //           -&gt;
    //         </span>
    //       </h2>
    //       <p classNameNameName={`m-0 max-w-[30ch] text-sm opacity-50 whitespace-pre-wrap ${descrStyle}`}>
    //         {status.connected ? status.info : "Establish connection to api server."}
    //       </p>
    //     </button>
    //     {/* Mock api endpoint button */}
    //     <button
    //       classNameNameName={`${buttonStyle} ${greyHoverStyle}`}
    //       onClick={mockAPIAction}
    //     >
    //       <h2 classNameNameName={`mb-3 text-2xl font-semibold`}>
    //         Mock API{" "}
    //         <span classNameNameName="inline-block transition-transform group-hover:translate-x-1 motion-reduce:transform-none">
    //           -&gt;
    //         </span>
    //       </h2>
    //       <p classNameNameName={`m-0 max-w-[30ch] text-sm opacity-50  ${descrStyle}`}>
    //         Example api server response from mock endpoint.
    //       </p>
    //     </button>
    //     {/* Start sidecar process button */}
    //     <button
    //       classNameNameName={`${buttonStyle} hover:border-gray-300 hover:bg-gray-100 hover:dark:border-green-500 hover:dark:bg-green-500/50`}
    //       onClick={startSidecarAction}
    //     >
    //       <h2 classNameNameName={`mb-3 text-2xl font-semibold`}>
    //         Start Sidecar{" "}
    //         <span classNameNameName="inline-block transition-transform group-hover:translate-x-1 motion-reduce:transform-none">
    //           -&gt;
    //         </span>
    //       </h2>
    //       <p classNameNameName={`m-0 max-w-[30ch] text-sm opacity-50  ${descrStyle}`}>
    //         Initialize a new sidecar process.
    //       </p>
    //     </button>
    //     {/* Shutdown sidecar process button */}
    //     <button
    //       classNameNameName={`${buttonStyle} hover:border-gray-300 hover:bg-gray-100 hover:dark:border-red-500 hover:dark:bg-red-500/50`}
    //       onClick={shutdownSidecarAction}
    //     >
    //       <h2 classNameNameName={`mb-3 text-2xl font-semibold`}>
    //         Stop Sidecar{" "}
    //         <span classNameNameName="inline-block transition-transform group-hover:translate-x-1 motion-reduce:transform-none">
    //           -&gt;
    //         </span>
    //       </h2>
    //       <p classNameNameName={`m-0 max-w-[30ch] text-sm opacity-50  ${descrStyle}`}>
    //         Force close the sidecar process.
    //       </p>
    //     </button>
    //   </div>
    // </main>
    <main>
    <div className="flex h-screen bg-gray-900 text-white">
      <div className="w-72 bg-gray-800 p-8 border-r border-gray-700">
        <h1 className="text-xl mb-4">Rouh.ai</h1>

        <select className="w-full bg-gray-700 border border-gray-600 rounded px-4 py-2 mt-4 text-white">
          <option value="gpt4">GPT-4</option>
          <option value="gpt35">GPT-3.5</option>  
          <option value="claude">Claude</option>
          <option value="llama">LLaMA</option>
          <option value="palm">PaLM</option>
        </select>

        <h2 className="text-lg mt-6 mb-4">About</h2>
        <p className="text-gray-400 text-sm leading-6 mb-6">
          Rouh is an AI assistant that can help you with various tasks, including browsing the web and interacting with
          your computer.
        </p>

        <h2 className="text-lg mt-6 mb-4">Usage</h2>
        <ul className="list-none space-y-2 text-gray-400 text-sm">
          <li className="flex items-center before:content-['•'] before:mr-2 before:text-gray-600">
            Type your message in the chat input
          </li>
          <li className="flex items-center before:content-['•'] before:mr-2 before:text-gray-600">
            Browser actions will be automatically detected
          </li>
        </ul>

        <h2 className="text-lg mt-6 mb-4">Features</h2>
        <ul className="list-none space-y-2 text-gray-400 text-sm">
          <li className="flex items-center before:content-['•'] before:mr-2 before:text-gray-600">Natural conversation</li>
          <li className="flex items-center before:content-['•'] before:mr-2 before:text-gray-600">
            Web browsing capabilities
          </li>
          <li className="flex items-center before:content-['•'] before:mr-2 before:text-gray-600">Computer interaction</li>
          <li className="flex items-center before:content-['•'] before:mr-2 before:text-gray-600">Screenshot capture</li>
        </ul>
      </div>

      <div className="flex-1 p-8 flex flex-col items-center">
        <div className="fixed top-4 right-4 flex gap-4">
          <button className="bg-gray-700 text-white px-4 py-2 rounded">RUNNING...</button>
          <button className="bg-gray-700 text-white px-4 py-2 rounded">Stop</button>
        </div>

        <div className="w-full max-w-4xl flex justify-center items-center h-full">
          <div className="space-y-4">
            <div className="bg-gray-800 rounded-lg p-6 text-gray-300">
              <p className="mb-4">
                I want to book a flight from Yatra.com for Dubai to Surat, Gujarat on 15th December, one-way trip for 1
                person. Search for the flight and select the first flight and go for booking until needed card details.
                Here are my details:
              </p>

              <ul className="mb-4 space-y-2">
                <li>Name → Ms. Vidhi Bhanderi</li>
                <li>Number → 6353355179</li>
                <li>Email → <a href="#" className="text-blue-500">vidhi@gmail.com</a></li>
                <li>Birthdate → 01/01/2002</li>
              </ul>

              <p className="mb-4">
                Book a seat from the recommendations and no need to add any extra meals or extra insurance. Just go
                straight till the booking and continue without travel insurance.
              </p>

              <p>Here are my UPI details for payment:</p>
              <ul className="space-y-2">
                <li>UPI ID → vidhibhanderi94@oksbi</li>
              </ul>
            </div>
          </div>
        </div>

        <div className="fixed bottom-0 left-72 right-0 bg-gray-900 border-t border-gray-700 p-4">
            <form onSubmit={handleSubmit} className="flex items-center bg-gray-800 rounded px-4 py-2">
              <input
                type="text"
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                onKeyPress={handleKeyPress}
                className="flex-1 bg-transparent border-none text-sm text-white placeholder-gray-600 focus:outline-none"
                placeholder="Type your message here..."
              />
              <button 
                type="submit"
                className="flex items-center justify-center p-2"
                disabled={!message.trim()}
              >
                <svg className="w-5 h-5 text-gray-600 hover:text-white" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
                </svg>
              </button>
            </form>
          </div>
      </div>
    </div>
    </main>
  );
}
