<p align="center">
  <a href="https://isaacadjei.me">Portfolio</a>
  &nbsp;&bull;&nbsp;
  <a href="https://isaacadjei.me/projects">Projects</a>
  &nbsp;&bull;&nbsp;
  <a href="https://isaacadjei.me/blog">Blog</a>
  &nbsp;&bull;&nbsp;
  <a href="https://isaacadjei.me/til">TIL</a>
  &nbsp;&bull;&nbsp;
  <a href="https://isaacadjei.me/newsletter">Newsletter</a>
  &nbsp;&bull;&nbsp;
  <a href="https://isaacadjei.me/links">Links</a>
  &nbsp;&bull;&nbsp;
  <a href="https://isaacadjei.me/contact">Contact</a>
  &nbsp;&bull;&nbsp;
  <a href="https://isaacadjei.me/all-pages">More</a>
</p>

<!--
  Profile card rendering:
  - <picture> with prefers-color-scheme serves profile-dark.svg or profile-light.svg directly to browser engines,
    ensuring light/dark mode switches reliably across every forge and device.
  - profile.svg serves as the standalone adaptive fallback card (dark theme by default with embedded CSS).
-->
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="profile-dark.svg?v=10">
  <source media="(prefers-color-scheme: light)" srcset="profile-light.svg?v=10">
  <img alt="Isaac Adjei's GitHub Profile" src="profile.svg?v=10" width="100%">
</picture>
<!-- I'm keeping this SVG but muting it for now - I'll uncomment when i want to restore it later -->
<!--
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="approach-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="approach-light.svg">
  <img alt="my approach" src="approach.svg" width="100%">
</picture>
-->
