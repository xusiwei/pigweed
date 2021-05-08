.. _module-pw_console:

----------
pw_console
----------

This directory contains the ``pw console`` interactive tool. It is under heavy
development and is not feature complete.

===========
Design
===========

Here's a diagram of how ``pw_console`` threads and asyncio tasks are organized.

.. mermaid::

   flowchart LR
       classDef eventLoop fill:#e3f2fd,stroke:#90caf9,stroke-width:1px;
       classDef thread fill:#fffde7,stroke:#ffeb3b,stroke-width:1px;
       classDef plugin fill:#fce4ec,stroke:#f06292,stroke-width:1px;
       classDef builtinFeature fill:#e0f2f1,stroke:#4db6ac,stroke-width:1px;

       %% Subgraphs are drawn in reverse order.

       subgraph pluginThread [Plugin Thread 1]
           subgraph pluginLoop [Plugin Event Loop 1]
               toolbarFunc-->|"Refresh<br/>UI Tokens"| toolbarFunc
               toolbarFunc[Toolbar Update Function]
           end
           class pluginLoop eventLoop;
       end
       class pluginThread thread;

       subgraph pluginThread2 [Plugin Thread 2]
           subgraph pluginLoop2 [Plugin Event Loop 2]
               paneFunc-->|"Refresh<br/>UI Tokens"| paneFunc
               paneFunc[Pane Update Function]
           end
           class pluginLoop2 eventLoop;
       end
       class pluginThread2 thread;

       subgraph replThread [Repl Thread]
           subgraph replLoop [Repl Event Loop]
               Task1 -->|Finished| Task2 -->|Cancel with Ctrl-C| Task3
           end
           class replLoop eventLoop;
       end
       class replThread thread;

       subgraph main [Main Thread]
           subgraph mainLoop [User Interface Event Loop]
               log[[Log Pane]]
               repl[[Python Repl]]
               pluginToolbar([User Toolbar Plugin])
               pluginPane([User Pane Plugin])
               class log,repl builtinFeature;
               class pluginToolbar,pluginPane plugin;
           end
           class mainLoop eventLoop;
       end
       class main thread;

       repl-.->|Run Code| replThread
       pluginToolbar-.->|Register Plugin| pluginThread
       pluginPane-.->|Register Plugin| pluginThread2
