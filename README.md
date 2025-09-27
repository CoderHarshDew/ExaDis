# ExaDis: The Blockchain Integrated Exam Paper Distribution System

### Problem: 
Even to this date, many examinations systems rely on traditional methods for exam paper distribution, which can result in leaks, which in turn undermines student's efforts, wastes time and resources, and may demans re-examination.

### Solution: 
This issue can be addressed through digitalization, encryption and distribution of power, which this system provides.

### Note:
This is a prototype version, and does not have complete functionality just yet.

---

# Table Of Contents

1. [Introduction.](#blockchain-integrated-exam-paper-distribution-system)
2. [Table of contents.](#table-of-contents)
3. [Features.](#features)
4. [Installation.](#installation)
5. [Usage.](#usage)
6. [FAQs.](#faqs)

---

# Features

### Encryption: 

- The exam paper is **encrypted** before saving on server / distribution, this ensures questions remain **confidential** even if file is leaked.
- **Split Key Cryptography:** Keys are split into N parts, out of which M parts must be brought together for decryption, this **prevents single point leaks.**
- Time + GPS + Account + Device locks for further security, ensures file can only be accessed at right time, location and by right person.

### No Direct Access To File:

- Encrypted file is stored on a server.
- File's location on server and its hash (digital fingerprint) is **uploaded to a blockchain.**
- Examination centers can only download the exam paper through the blockchain, this **prevents direct access to file.**
- Additionally, the blockchain **cross-verifies the file integrity** and detects if file at source (server) has been tampered with or not, **ensuring exam paper originality.**

### Server Features:

- Files are not downloadable by default.
- Can only be made downloadable through consent of multiple admins, ensures even **admins need to work together** for major changes.
- Same for other major changes.

### Account Security:

- Only admins can create, modify or delete account, others can only log in.
- Admins can remotely log out non-admins.

### Audits and watermarks:

- Decryption system leaves a watermark on decrypted file, **allows to easily traceback leaks** to leaking point.
- All activities are logged to a blockchain, **ensures transparency**.
- Physical copies can also be watermarked similarly.

### Other Features:

- **Offline first support:** Allows to decrypt file offline, logs are synced later to blockchain when connection is available.
- **Modular Development:** Allows easy development and updates.

### To Be Added:

- Time + GPS + Account + Device locks in encryption.
- Blockchain.
- Admin side account controls.
- Server, (currently using simulated version).

---

# Installation

1. **Clone the repository:**
``` 
git clone https://github.com/CoderHarshDew/ExaDis.git
cd ExaDis

```
2. **Install Dependencies:**
```
pip install -r requirements.txt

```

---

# Usage

1. **Start encryption system:**
```
python enc_app_frontend.py

```
2. **Start decryption system:**
```
python dec_app_frontend.py

```
3. **Start the server system:**
```
python server_system_frontend.py

```
