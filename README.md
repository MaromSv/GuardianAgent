# Guardian Agent
this is the repo for the Junction 2025 hackathon in Espoo team TiramAIsu (Marom Sverdlov and Oliver Erven). We fully build the entire codebase in around 24 hours of work. 

## Motivation
Our parents and grandparents are getting older, and the world around them is getting more complicated.  
Phone scams are no longer clumsy attempts from strangers with broken English — AI has given scammers polished voices, convincing scripts, and the ability to sound like trusted companies or even family members. 

Last year alone, millions of people were targeted by phone scams worldwide, with billions of euros lost, and the numbers are rising fast.  
It’s easy to think that it could never happen to you or your family, but that's exactly what everybody who got scammed thought as well.

We built TiramAIsu because we wanted something real, something that actually steps in *during* the call, not after the damage is done.  
Not another article warning “watch out for scams” but a system that listens, understands, and acts when it matters.

TiramAIsu is an all-encompassing safety layer. 
An AI guardian that silently monitors phone calls from unknown numbers, detects scam signals, and only speaks when someone you love might be in danger.  
It can stop scams in real time, step in to question suspicious callers, automatically hang up when a scam is detected, notify family members, and even report the number to help prevent the same scam from happening to someone else in the future.


## Features
- **Live call monitoring** through a real-time voice agent that listens quietly in the background  
- **Advanced scam detection** using phone-number reputation checks, linguistic analysis, behavioral cues, and intent modeling  
- **Real-time intervention**  
  - Asks legitimacy-checking questions when something feels suspicious  
  - Issues strong warnings when danger is confirmed  
  - Can automatically **hang up** on the scammer to protect the user  
- **Family safety alerts**, instantly sends SMS notifications to family members if a high-risk call occurs
- **Automatic scam reporting** to help stop the same number from targeting other victims in the future. 
- **Demo frontend** for visualizing ongoing calls, risk levels, transcripts, and agent decisions (E2E encrypted by default; intended for demonstration and debugging).

## Getting Started


### Installation
```bash
git clone https://github.com/your-org/tiramaisu.git
cd tiramaisu
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
```