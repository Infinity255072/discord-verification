# discord-verification
Discord Bot mit Verifikationssystem in 2 Phasen: einer Email Verifikation und einer "Introduction", bei dem der User einige Infos über sich angibt.

Dieser Discord Bot ist ein Projekt welches ich ungefähr Anfang letzen Jahres für einen guten Freund von mir begonnen habe. Er hat eine eigene Discord Community bei der sich Personen über Business, neue Ideen, Projekte und self-improvement unterhalten können. Die Community umfasst circa 1.500 User auf dem Discord.
Das System für die "introduce.py" Datei ist zugegeben etwas chaotisch, da es in der Entwicklung oft angepasst oder komplett geändert wurde. Ich habe Code Kommentare an ein paar stellen hinzugefügt, um wichtige Funktionen kurz zu erklären.

Ich benutze zum coding des Bots "py-cord".

## Features
- Verwendet smtp um eine Verifikationsemail zu schicken.
- Speichert u.a. Verifikationsdaten in einer aiosqlite Datenbank.
- Sichert wichtige Daten wie den Bot Token in einer .env Umgebung.
- Verwaltet ein BEEHIIV Newsletter für die Community.
- User können sich über Discord direkt Vorstellen, um Zugriff auf mehr Funktionen der Community zu bekommen und den Verifikationsprozess abzuschließen.
