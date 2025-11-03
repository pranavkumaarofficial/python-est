# Diagrams for Medium Article

## Diagram 1: EST Bootstrap Flow (Place after "Deep Dive: The Bootstrap Flow" section)

```mermaid
sequenceDiagram
    participant Device
    participant EST Server
    participant CA

    Note over Device: Step 1: Generate Key Pair
    Device->>Device: Generate RSA 2048 private key
    Device->>Device: Keep private key secure (NEVER transmitted)

    Note over Device: Step 2: Create CSR
    Device->>Device: Create CSR with device ID as CN
    Device->>Device: Sign CSR with private key

    Note over Device,EST Server: Step 3: POST CSR to Bootstrap
    Device->>EST Server: POST /.well-known/est/bootstrap<br/>(CSR + Basic Auth)
    EST Server->>EST Server: Validate username/password
    EST Server->>EST Server: Parse CSR, extract device ID
    EST Server->>EST Server: Check for duplicate device ID

    Note over EST Server,CA: Step 4: Sign Certificate
    EST Server->>CA: Sign certificate request
    CA->>CA: Validate CSR signature
    CA->>CA: Generate X.509 certificate
    CA->>CA: Add KeyUsage extensions
    CA->>EST Server: Return signed certificate

    Note over EST Server: Step 5: Wrap in PKCS#7
    EST Server->>EST Server: Create PKCS#7 SignedData
    EST Server->>EST Server: Include cert + CA chain
    EST Server->>Device: 200 OK<br/>(PKCS#7 response)

    Note over Device: Step 6: Extract Certificate
    Device->>Device: Parse PKCS#7 structure
    Device->>Device: Extract certificate
    Device->>Device: Save certificate + private key

    Note over Device: ✅ Device is now enrolled!
```

**Caption**: *The complete EST bootstrap flow. Notice that the private key is generated on the device and never transmitted to the server — this is critical for security.*

---

## Diagram 2: System Architecture (Place after "The Architecture: How It Actually Works" section)

```mermaid
graph TB
    subgraph "Client Side"
        Device[IoT Device]
        Client[EST Client Library]
    end

    subgraph "EST Server"
        FastAPI[FastAPI Server<br/>Port 8445]
        Auth[Authentication<br/>SRP / HTTP Basic]
        DeviceTracker[Device Tracker<br/>JSON Storage]
        Dashboard[Web Dashboard<br/>React UI]
    end

    subgraph "Certificate Authority"
        CA[CA Module<br/>Sign Certificates]
        CAKey[CA Private Key<br/>ENCRYPTED]
        CACert[CA Certificate<br/>Trust Anchor]
    end

    subgraph "Storage"
        JSON[Device Database<br/>device_tracking.json]
        Certs[Certificate Storage<br/>Serial Numbers Only]
    end

    Device -->|1. Generate CSR| Client
    Client -->|2. HTTPS POST| FastAPI
    FastAPI -->|3. Authenticate| Auth
    Auth -->|4. Check Duplicate| DeviceTracker
    DeviceTracker -->|5. Read/Write| JSON
    FastAPI -->|6. Sign Request| CA
    CA -->|7. Load Keys| CAKey
    CA -->|8. Load Cert| CACert
    CA -->|9. Return PKCS#7| FastAPI
    FastAPI -->|10. Response| Client
    Client -->|11. Save Cert| Device
    DeviceTracker -->|Track| Certs
    Dashboard -->|Query Stats| DeviceTracker

    style Device fill:#e1f5e1
    style FastAPI fill:#e3f2fd
    style CA fill:#fff3e0
    style JSON fill:#f3e5f5
    style CAKey fill:#ffebee
```

**Caption**: *Python-EST system architecture. The server never touches device private keys — it only signs CSRs and returns certificates in PKCS#7 format.*

---

## Diagram 3: Enrollment vs Re-enrollment Flow (Place after "Real-World Use Cases" section)

```mermaid
graph TD
    Start[Device Needs Certificate] --> HasCert{Has Valid<br/>Certificate?}

    HasCert -->|No| Bootstrap[Bootstrap Flow]
    Bootstrap --> GenKey[Generate Private Key]
    GenKey --> CreateCSR[Create CSR]
    CreateCSR --> PostBootstrap[POST /.well-known/est/bootstrap<br/>Username + Password]
    PostBootstrap --> ReceiveBootstrap[Receive Bootstrap Certificate]
    ReceiveBootstrap --> Done[✅ Enrolled]

    HasCert -->|Yes, Expiring| Renewal[Re-enrollment Flow]
    Renewal --> CreateRenewalCSR[Create New CSR]
    CreateRenewalCSR --> PostRenew[POST /.well-known/est/simplereenroll<br/>Client Certificate Auth]
    PostRenew --> ReceiveNew[Receive New Certificate]
    ReceiveNew --> Done

    HasCert -->|Yes, Valid| Wait[Wait Until Near Expiry]
    Wait --> CheckExpiry[Check Expiry in 10 Days?]
    CheckExpiry -->|Yes| Renewal
    CheckExpiry -->|No| Wait

    Done --> Monitor[Monitor Certificate Expiry]
    Monitor --> CheckExpiry

    style Bootstrap fill:#ffebee
    style Renewal fill:#e8f5e9
    style Done fill:#c8e6c9
```

**Caption**: *Device enrollment lifecycle. Bootstrap is used once for initial enrollment, then re-enrollment (with client certificate authentication) handles renewals.*

---

## Diagram 4: Comparison Matrix (Place in "Comparison" section)

```mermaid
graph LR
    subgraph "Python-EST"
        PE1[✅ Native Python]
        PE2[✅ Easy Integration]
        PE3[✅ Modern FastAPI]
        PE4[⚠️ New Project]
        PE5[⚠️ Missing CRL/OCSP]
    end

    subgraph "libest C"
        LE1[✅ Battle-tested]
        LE2[✅ High Performance]
        LE3[❌ C Complexity]
        LE4[❌ Hard to Extend]
        LE5[❌ OpenSSL Dependencies]
    end

    subgraph "Java EST"
        JE1[✅ Enterprise Features]
        JE2[✅ Good Docs]
        JE3[❌ JVM Required]
        JE4[❌ Heavy Footprint]
        JE5[❌ Not Python-Friendly]
    end

    subgraph "Roll Your Own"
        RY1[✅ Full Control]
        RY2[❌ Weeks of Work]
        RY3[❌ Security Risks]
        RY4[❌ No RFC Compliance]
        RY5[❌ Maintenance Burden]
    end

    style PE1 fill:#c8e6c9
    style PE2 fill:#c8e6c9
    style PE3 fill:#c8e6c9
    style PE4 fill:#fff9c4
    style PE5 fill:#fff9c4

    style LE1 fill:#c8e6c9
    style LE2 fill:#c8e6c9
    style LE3 fill:#ffcdd2
    style LE4 fill:#ffcdd2
    style LE5 fill:#ffcdd2

    style JE1 fill:#c8e6c9
    style JE2 fill:#c8e6c9
    style JE3 fill:#ffcdd2
    style JE4 fill:#ffcdd2
    style JE5 fill:#ffcdd2

    style RY1 fill:#c8e6c9
    style RY2 fill:#ffcdd2
    style RY3 fill:#ffcdd2
    style RY4 fill:#ffcdd2
    style RY5 fill:#ffcdd2
```

**Caption**: *Feature comparison of EST server implementations. Python-EST offers the best developer experience for Python-first organizations.*

---

## How to Use These Diagrams

### Option 1: Render to Images (Recommended for Medium)

Use one of these tools to convert Mermaid to PNG/SVG:

**Online Tools**:
1. https://mermaid.live/ (paste code, download image)
2. https://mermaid.ink/ (generate shareable image URLs)

**Command Line** (if you have mermaid-cli installed):
```bash
npm install -g @mermaid-js/mermaid-cli

# Convert to PNG
mmdc -i diagram1.mmd -o diagram1.png -w 1200 -H 800 -b white

# Convert to SVG (better quality)
mmdc -i diagram1.mmd -o diagram1.svg -w 1200 -H 800 -b white
```

### Option 2: Use Medium's Code Blocks

Medium doesn't natively render Mermaid, but you can:
1. Convert to images using mermaid.live
2. Upload images to Medium
3. Place images at suggested locations in article

### Suggested Image Placement

1. **Diagram 1 (Bootstrap Flow)**: After "Deep Dive: The Bootstrap Flow" heading
   - Shows the complete step-by-step enrollment process
   - Helps readers visualize the CSR → Certificate flow

2. **Diagram 2 (Architecture)**: After "The Architecture: How It Actually Works" heading
   - Shows how FastAPI, CA, and Device Tracker interact
   - Illustrates the separation of concerns

3. **Diagram 3 (Enrollment Lifecycle)**: After "Real-World Use Cases" section
   - Shows bootstrap vs re-enrollment decision tree
   - Helps readers understand when to use each flow

4. **Diagram 4 (Comparison)**: In "Comparison: Python-EST vs The Alternatives" section
   - Visual comparison of features
   - Makes trade-offs immediately clear

---

## Additional Diagram Ideas (Optional)

If you want more visuals, here are some additional diagrams you could create:

### 5. Security Layers Diagram
```
[ TLS 1.2/1.3 Transport ]
    ↓
[ HTTP Basic Auth ]
    ↓
[ CSR Signature Verification ]
    ↓
[ Duplicate Device Check ]
    ↓
[ Certificate Generation ]
```

### 6. Deployment Options Diagram
```
                    ┌─────────────┐
                    │   Client    │
                    └──────┬──────┘
                           │
                           ↓
              ┌────────────────────────┐
              │   Load Balancer        │
              └────────┬───────────────┘
                       │
       ┌───────────────┼───────────────┐
       ↓               ↓               ↓
   ┌───────┐      ┌───────┐      ┌───────┐
   │EST-1  │      │EST-2  │      │EST-3  │
   └───┬───┘      └───┬───┘      └───┬───┘
       │              │              │
       └──────────────┼──────────────┘
                      ↓
              ┌───────────────┐
              │  PostgreSQL   │
              └───────────────┘
```

### 7. Certificate Expiry Timeline
```
Day 0     Day 30    Day 60    Day 80    Day 90
  │─────────│─────────│─────────│─────────│
  ↓         ↓         ↓         ↓         ↓
Issued    OK        OK      Renew!   Expired
                             Alert
```

---

## Diagram Customization Tips

**Color Schemes**:
- Green (#c8e6c9): Success states, secure operations
- Red (#ffcdd2): Failures, security issues
- Yellow (#fff9c4): Warnings, needs attention
- Blue (#e3f2fd): Neutral, informational

**Font Sizes** (for export):
- Title: 20px
- Node text: 14px
- Arrow labels: 12px

**Image Dimensions**:
- Width: 1200px (standard Medium width)
- Height: Auto (maintain aspect ratio)
- Format: PNG or SVG (SVG preferred for quality)
- DPI: 144 (for retina displays)

---

## Quick Start: Generating Images Now

**Fastest method** (no installation required):

1. Go to https://mermaid.live/
2. Copy Diagram 1 code (the sequence diagram)
3. Paste into left panel
4. Click "Download PNG" (top right)
5. Repeat for all 4 diagrams

**Total time**: 5 minutes for all diagrams

---

## Accessibility Notes

When adding these images to Medium, include alt text:

- Diagram 1: "Sequence diagram showing EST bootstrap flow from device key generation through certificate enrollment"
- Diagram 2: "Architecture diagram of Python-EST server components including FastAPI, CA module, and device tracker"
- Diagram 3: "Flowchart showing device enrollment lifecycle with bootstrap and re-enrollment paths"
- Diagram 4: "Comparison matrix of EST server implementations showing pros and cons of each approach"

This ensures screen readers can describe the diagrams to visually impaired readers.
