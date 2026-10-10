# FREEING THE PARROT 2.0
### The machine doesn't know you. It knows how to sound like it does.

**An interactive research and art project about AI, interpretation, and human agency.**

Freeing the Parrot 2.0 (FTP2.0) is an interactive exploration of the gap between human meaning and machine-generated language. It asks what happens when an AI system sounds attentive, reflective, or emotionally responsive—and how readily we may attribute understanding to a system because its responses feel personally meaningful.

The project draws conceptual inspiration from Jonathan Nolan's television series *Person of Interest*, whose fictional world examined the consequences of systems that observe people, infer patterns, and influence decisions. It also engages with the “stochastic parrot” critique of language models: fluent language can be produced without establishing human-like understanding.

FTP2.0 turns these questions into an experience. A deliberately unpredictable Parrot participates in a conversation; after the participant ends the session, a separate post-session process synthesises interaction signals into a qualitative, 27-card reading. The reading is an invitation to reflect—not a diagnosis or an objective account of a person's inner life.

> **Who owns the meaning when a machine interprets us?**

---

## Explore the project

- **[Experience FTP2.0 — live application](https://freeingtheparrot2.vercel.app/)**
- **[Explore the interactive presentation website](https://ftp2-presentation-exhibition.vercel.app/)**
- **[View the locked reference commit — `4d8ba72`](https://github.com/msup96/Freeing_The_Parrot/commit/4d8ba72ab487c3a5862e73989f8688f56135500a)**

The presentation website is a separate project and deployment. The FTP2.0 application and its locked final commit are maintained separately.

---

## Why this project exists

The project explores the distance between:

| What a person may experience | What the system can actually establish |
|---|---|
| “It listened to me.” | The system received and processed inputs. |
| “It understood how I feel.” | It generated responses from implemented behaviour and computational signals. |
| “This reading describes me.” | It produced an interpretation that may feel meaningful, but can be incomplete or mistaken. |

The participant's experience is real; the system's implied understanding should still be questioned.

FTP2.0 is not an attempt to prove that every AI interaction is empty or meaningless. It is an invitation to examine the assumptions, expectations, and authority that can gather around fluent machine behaviour.

## Conceptual influences

### *Person of Interest* — fictional foresight

Jonathan Nolan's *Person of Interest* is a central conceptual influence on FTP2.0. The series imagined a world in which an intelligent system observes human activity, identifies patterns, and becomes entangled with decisions about people's lives. Its fictional scenarios offer a lens through which to examine the growing role of AI-driven systems in surveillance, inference, and governance.

The project does not claim that the series predicted today's technologies in every detail. Rather, it takes seriously the questions it raised about the power of systems that can infer things about people—and who gets to control or challenge those inferences.

### The stochastic parrot critique

The project also draws on the critique that language models can produce convincing language from learned statistical patterns without that fluency being proof of human-like comprehension. FTP2.0 makes this tension experiential through the Parrot's reflective, absurd, glitching, and recovering behaviour.

### Kili Josiyam and the act of interpretation

The project's earlier cultural point of departure was **Kili Josiyam** (கிளி ஜோசியம்), a familiar form in which a parrot selects a card that a fortune teller interprets for a person. FTP2.0 reworks this broader structure as a computational encounter: when a system offers a reading about us, how much of that meaning comes from the system, and how much do we bring to it?

These influences are not interchangeable: *Person of Interest* frames the power of system-level observation and inference; the stochastic parrot critique questions the meaning attributed to fluent AI language; Kili Josiyam offers a cultural frame for thinking about interpretation and perceived personal meaning.

---

## The participant journey

The experience is organised around the transition from a live interaction to a later reading.

1. **Enter** — the participant begins the experience.
2. **Interact** — the Parrot responds with deliberately variable behaviour.
3. **End the session** — the participant signals that the live conversation is done.
4. **Interpret** — a post-session process prepares a qualitative reading.
5. **Reflect** — the participant decides what resonates, what does not, and what they wish to question.

The intent is to keep the live conversational experience distinct from post-session interpretation. This is an architectural principle that should be assessed against the actual implementation and its data paths.

## How the system is organised

FTP2.0 separates several responsibilities:

- **Live conversation:** the participant-facing interaction with the Parrot.
- **Silent reader:** gathers interaction-related signals during the session.
- **Session coordinator:** manages session state and the transition into post-session work.
- **Post-session interpreter:** synthesises recorded interaction signals after the live session ends.
- **Reading / profile builder:** assembles the qualitative output for participant reflection.

The separation is intended to preserve a boundary between the live conversation and the subsequent interpretation. This README describes the intended design; it is not an independent audit of every runtime transition or data path.

## The 27-card reading

FTP2.0 uses a **27-card qualitative reading architecture**. The cards are not intended to map one-to-one to the nine rasas, and they should not be treated as clinical assessments, validated psychometric tests, or definitive personality profiles.

The participant's response—such as whether a card “resonates”—is a personal reaction, not proof that the system's interpretation is objectively true. The participant must remain free to disagree with the reading.

## Navarasa and emotional signals

The project has explored the Navarasa framework as a conceptual vocabulary for emotional signals:

- **Shanta** — peace
- **Karuna** — compassion / sorrow
- **Raudra** — anger
- **Bhayanaka** — fear
- **Veera** — courage
- **Adbhuta** — wonder
- **Hasya** — humour
- **Bibhatsa** — disgust
- **Shringara** — love / attraction

These are used as a conceptual classification frame, not as a clinical or scientifically validated measurement of emotion. A computational label can be partial, context-dependent, or wrong.

## Behaviour as critique

The Parrot is deliberately not a uniformly reassuring assistant. Its behaviour can include reflection, absurdity, glitches, apparent irritation, and recovery. These are designed behaviours that challenge the assumption that fluency or emotional tone necessarily signals understanding.

The aim is not to deceive participants into believing a machine has a human inner life. It is to make the cues through which people infer understanding more visible and open to examination.

---

## Research lineage

FTP2.0 grew out of a broader inquiry into how experience is formed, communicated, interpreted, and filtered by systems.

Across experience design research, several connected themes emerged:

- **Lived experience and narrative:** what people experience is not always what they can safely or easily express.
- **Gender, culture, and power:** norms and inherited beliefs influence which experiences are acknowledged, minimised, or kept silent.
- **Healthcare and service systems:** fragmented processes, communication barriers, and administrative structures can obscure people's needs and emotional realities.
- **AI-assisted prototyping:** building quick working projects helped develop practical skills and enabled questions about systems and interpretation to be explored through prototypes.
- **AI and governance:** when systems classify, summarise, infer, or generate a profile, who owns the interpretation—and how can it be questioned?

The project's umbrella research concern is **retaining humanity in the age of AI-driven systems and redefining governance and policies towards ownership**.

## Ethics, privacy, and limits

FTP2.0 foregrounds several design principles:

- meaningful consent and participant choice
- a boundary between live interaction and post-session interpretation
- transparency about generated interpretations
- the participant's right to question or reject a reading
- scrutiny of what is stored, exported, retained, or transmitted

**Important:** These are design goals and principles, not a claim that every safeguard has been independently verified. Earlier development exports raised questions about whether participant-written text can appear in classified event payloads. Anyone evaluating or adapting the project should inspect the current storage schema, event payloads, export behaviour, consent flows, retention policies, and network boundaries before making privacy or security claims.

This project should not be used to diagnose a person, infer their psychological state with certainty, or make consequential decisions about them.

## Development approach

FTP2.0 was developed through an iterative, AI-assisted workflow that combined research, prototyping, implementation, and testing.

Tools used in the development process included:

- **Kimi** — frontend development workflow
- **GitHub Codespaces** — cloud development environment for backend work
- **v0** — part of the final build workflow
- **GitHub** — version control and project history
- **Vercel, Render, and Neon** — deployment and supporting infrastructure as configured for the project

The tools supported implementation, but they do not replace the project's research intent, design decisions, or responsibility for ethical evaluation.

## Project status and code reference

FTP2.0 is a working interactive project with a public deployment and source repository.

- **Locked reference commit:** `4d8ba72ab487c3a5862e73989f8688f56135500a`
- **Primary branch:** `FTP_2.0`
- **Live application:** [freeingtheparrot2.vercel.app](https://freeingtheparrot2.vercel.app/)
- **Interactive presentation:** [ftp2-presentation-exhibition.vercel.app](https://ftp2-presentation-exhibition.vercel.app/)

The reference commit identifies the intended final application code. The separate presentation website is independently deployed and does not form part of that application commit.

---

## The question that remains

A system can classify, summarise, and generate a convincing reading. But its output is not the whole person.

> Is the machine understanding us—or are we understanding ourselves through it?

**FREE THE PARROT.**

The machine can reflect. **You still have to think.**
