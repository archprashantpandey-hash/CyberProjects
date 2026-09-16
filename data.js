const projects = [

    {
        id: "ephemeral-dev-sandbox",

        title: "Automated Ephemeral Development Sandbox",

        category: "Systems",

        status: "Building",

        description:
            "CLI-driven disposable Linux development environments that can be created, snapshotted and destroyed on demand.",

        technologies: [
            "Linux",
            "Incus",
            "systemd",
            "ZFS/BTRFS",
            "Gum",
            "Bash"
        ],

        icon: "⌘",

        favorite: true,

        details: {

            problem:
                "Development environments become cluttered, inconsistent and difficult to reproduce.",

            solution:
                "Create isolated disposable environments from reusable blueprints and automatically destroy them after use.",

            architecture: [
                "CLI interface",
                "Incus container layer",
                "systemd lifecycle daemon",
                "Snapshot engine",
                "Recipe engine",
                "Resource limiter"
            ],

            features: [
                "Create disposable Linux environments",
                "Automatic lifecycle management",
                "Checkpoint and rollback",
                "Node.js / Python / web recipes",
                "CPU and memory throttling",
                "Reusable Incus profiles",
                "Rich terminal interface"
            ],

            example:
                "./sandbox.sh create --recipe nodejs",

            questions: [
                "How should failed environments be recovered?",
                "Should environments support GPU access?",
                "How should persistent project data be separated from disposable state?"
            ]

        }
    },


    {
        id: "chaos-network-proxy",

        title: "Chaos Network Proxy",

        category: "Networking",

        status: "Researching",

        description:
            "A controlled network fault-injection tool that simulates latency, packet loss and unreliable network conditions.",

        technologies: [
            "Linux tc",
            "iptables",
            "nftables",
            "Bash",
            "Networking"
        ],

        icon: "⌁",

        favorite: true,

        details: {

            problem:
                "Applications often behave differently under poor network conditions, but developers usually test only on reliable networks.",

            solution:
                "Provide a CLI for deliberately injecting network faults into selected traffic.",

            architecture: [
                "CLI controller",
                "Traffic classifier",
                "tc network emulator",
                "iptables/nftables rules",
                "Statistics collector"
            ],

            features: [
                "Artificial latency",
                "Packet loss",
                "Bandwidth throttling",
                "Packet duplication",
                "Traffic targeting",
                "Rule cleanup"
            ],

            example:
                "./chaos --target github.com --latency 500ms --packet-loss 10%",

            questions: [
                "How should traffic be selected safely?",
                "Can profiles be created for common failure scenarios?",
                "Should the tool provide real-time graphs?"
            ]

        }
    },


    {
        id: "reverse-proxy-tunnel",

        title: "Multi-Tenant Reverse Proxy Tunnel",

        category: "Networking",

        status: "Idea",

        description:
            "A self-hosted ngrok-style tunnel that exposes local services through a controlled cloud relay.",

        technologies: [
            "Go",
            "TCP",
            "SSH",
            "Cloud VM",
            "TLS"
        ],

        icon: "⇄",

        favorite: false,

        details: {

            problem:
                "Developers need temporary public access to locally running services without manually configuring routers or port forwarding.",

            solution:
                "Use a cloud relay and client agent to establish authenticated reverse tunnels.",

            architecture: [
                "Local agent",
                "Cloud relay",
                "Tunnel multiplexer",
                "TLS layer",
                "Authentication layer"
            ],

            features: [
                "Temporary tunnels",
                "Multiple tenants",
                "TLS encryption",
                "Automatic reconnect",
                "Port forwarding",
                "Tunnel management CLI"
            ],

            example:
                "./tunnel expose 8080",

            questions: [
                "How should tenant isolation work?",
                "Should multiplexing use HTTP/2 or a custom protocol?",
                "How should tunnel authentication be handled?"
            ]

        }
    },


    {
        id: "zero-trust-ssh",

        title: "Zero-Trust Ephemeral SSH Gateway",

        category: "Security",

        status: "Researching",

        description:
            "Temporary SSH access using short-lived OpenSSH certificates instead of permanent credentials.",

        technologies: [
            "OpenSSH",
            "SSH Certificates",
            "Mini CA",
            "Linux",
            "systemd"
        ],

        icon: "◇",

        favorite: true,

        details: {

            problem:
                "Permanent SSH keys create long-lived access that can remain valid after the original task is finished.",

            solution:
                "Issue short-lived SSH certificates that naturally expire after a defined access window.",

            architecture: [
                "Certificate authority",
                "Access gateway",
                "Certificate issuer",
                "Target servers",
                "Audit log"
            ],

            features: [
                "15-minute access windows",
                "Short-lived certificates",
                "Central CA",
                "Access logging",
                "Automatic expiration"
            ],

            example:
                "ssh-keygen -s team-ca -I temporary-user -n developer -V +15m user-key.pub",

            questions: [
                "How should emergency access work?",
                "How should certificates be audited?",
                "Should approval workflows be added?"
            ]

        }
    },


    {
        id: "gitops-db",

        title: "Live Git-Ops Database Branching Engine",

        category: "DevSecOps",

        status: "Idea",

        description:
            "Automatically create isolated database environments alongside Git branches using filesystem snapshots and copy-on-write clones.",

        technologies: [
            "Git",
            "PostgreSQL",
            "ZFS",
            "BTRFS",
            "Docker"
        ],

        icon: "⑂",

        favorite: false,

        details: {

            problem:
                "Feature branches frequently require isolated database states, but cloning large databases is slow and expensive.",

            solution:
                "Create copy-on-write database environments from filesystem snapshots when branches change.",

            architecture: [
                "Git hook",
                "Snapshot manager",
                "Database template",
                "CoW clone",
                "Environment manager"
            ],

            features: [
                "Branch-aware databases",
                "Fast snapshots",
                "Automatic cleanup",
                "Database lifecycle management",
                "Environment naming"
            ],

            example:
                "git checkout feature/payment",

            questions: [
                "How should migrations be handled?",
                "What happens when branches are deleted?",
                "Can PostgreSQL and MySQL use the same abstraction?"
            ]

        }
    },


    {
        id: "ebpf-flight-recorder",

        title: "eBPF Black Box Flight Recorder",

        category: "Systems",

        status: "Idea",

        description:
            "A lightweight Linux observability agent that continuously retains recent low-level system events and preserves them when something goes wrong.",

        technologies: [
            "eBPF",
            "BCC",
            "Tetragon",
            "Linux",
            "BPF Ring Buffer"
        ],

        icon: "◉",

        favorite: true,

        details: {

            problem:
                "Many failures become difficult to investigate because the important system events happened shortly before the failure.",

            solution:
                "Maintain a rolling buffer of low-level events and dump the recent history when a trigger occurs.",

            architecture: [
                "eBPF probes",
                "Kernel event collection",
                "BPF ring buffer",
                "Circular event store",
                "Trigger engine",
                "Crash dump"
            ],

            features: [
                "Rolling 60-second event buffer",
                "Process execution tracking",
                "File access events",
                "Network events",
                "Crash-triggered dumps",
                "Low overhead collection"
            ],

            example:
                "sys_enter_execve → BPF ring buffer → circular store",

            questions: [
                "How much data can be retained safely?",
                "Which events provide the most diagnostic value?",
                "How should sensitive data be filtered?"
            ]

        }
    },


    {
        id: "hardware-secrets",

        title: "Hardware-Backed Ephemeral Secrets Safe",

        category: "Hardware",

        status: "Idea",

        description:
            "A local credential vault that uses TPM-backed cryptographic protection to make stored secrets dependent on trusted hardware.",

        technologies: [
            "TPM 2.0",
            "tpm2-tools",
            "Linux",
            "Cryptography",
            "SQLite"
        ],

        icon: "⬡",

        favorite: false,

        details: {

            problem:
                "Local credential databases can expose sensitive secrets if copied or accessed outside the intended environment.",

            solution:
                "Use TPM-backed keys to protect a local encrypted secrets store and release secrets only through controlled runtime operations.",

            architecture: [
                "CLI",
                "Encrypted database",
                "TPM key",
                "Policy engine",
                "Runtime secret injector"
            ],

            features: [
                "TPM-backed encryption",
                "Encrypted local database",
                "Runtime secret injection",
                "Hardware-bound key policies",
                "CLI interface"
            ],

            example:
                "vault get DATABASE_PASSWORD",

            questions: [
                "What threat model should be supported?",
                "How should TPM recovery work?",
                "Should secrets ever be written to disk after decryption?"
            ]

        }
    }

];