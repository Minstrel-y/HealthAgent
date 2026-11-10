<template>
  <svg
    :width="size"
    :height="size * 1.25"
    viewBox="0 0 200 250"
    fill="none"
    class="cloud"
    :class="{ floating: glow }"
  >
    <defs>
      <!-- 云朵体积感：左上偏白，右下偏灰蓝 -->
      <radialGradient id="cloudBody" cx="0.38" cy="0.3" r="0.85">
        <stop offset="0%" stop-color="#ffffff" />
        <stop offset="62%" stop-color="#fdfefe" />
        <stop offset="100%" stop-color="#e8f0f8" />
      </radialGradient>

      <linearGradient id="goldRing" x1="0" y1="0" x2="1" y2="0">
        <stop offset="0%" stop-color="#f5cf6a" />
        <stop offset="45%" stop-color="#ffe9a8" />
        <stop offset="100%" stop-color="#e0b34a" />
      </linearGradient>

      <linearGradient id="scarf" x1="0" y1="0" x2="0.4" y2="1">
        <stop offset="0%" stop-color="#a7e0d0" />
        <stop offset="100%" stop-color="#7fcbb7" />
      </linearGradient>

      <radialGradient id="orbGlow" cx="0.45" cy="0.4" r="0.65">
        <stop offset="0%" stop-color="#fffbe8" />
        <stop offset="45%" stop-color="#ffe27a" />
        <stop offset="100%" stop-color="#f6c33c" />
      </radialGradient>

      <filter id="softShadow" x="-30%" y="-20%" width="160%" height="150%">
        <feDropShadow dx="0" dy="6" stdDeviation="9" flood-color="#a9c3dc" flood-opacity="0.38" />
      </filter>

      <filter id="orbFilter" x="-120%" y="-120%" width="340%" height="340%">
        <feGaussianBlur stdDeviation="5" result="blur" />
        <feMerge>
          <feMergeNode in="blur" />
          <feMergeNode in="SourceGraphic" />
        </feMerge>
      </filter>
    </defs>

    <!-- 头顶光环 -->
    <ellipse
      cx="100" cy="30" rx="42" ry="11"
      stroke="url(#goldRing)" stroke-width="6" fill="none"
      transform="rotate(-6 100 30)"
    />
    <ellipse
      cx="100" cy="30" rx="42" ry="11"
      stroke="#fff6d8" stroke-width="1.6" fill="none" opacity="0.9"
      transform="rotate(-6 100 30)"
    />

    <!-- 云朵主体 -->
    <g filter="url(#softShadow)">
      <circle cx="56" cy="142" r="43" fill="url(#cloudBody)" />
      <circle cx="100" cy="116" r="52" fill="url(#cloudBody)" />
      <circle cx="144" cy="142" r="43" fill="url(#cloudBody)" />
      <rect x="14" y="132" width="172" height="70" rx="35" fill="url(#cloudBody)" />
    </g>

    <!-- 小短手 -->
    <ellipse cx="22" cy="176" rx="12" ry="15" fill="url(#cloudBody)" />
    <ellipse cx="178" cy="176" rx="12" ry="15" fill="url(#cloudBody)" />

    <!-- 眼睛 -->
    <ellipse cx="82" cy="130" rx="7.5" ry="9" fill="#22303f" />
    <ellipse cx="118" cy="130" rx="7.5" ry="9" fill="#22303f" />
    <circle cx="84.6" cy="126.4" r="2.6" fill="#ffffff" />
    <circle cx="120.6" cy="126.4" r="2.6" fill="#ffffff" />
    <circle cx="79.6" cy="133" r="1.2" fill="#ffffff" opacity="0.75" />
    <circle cx="115.6" cy="133" r="1.2" fill="#ffffff" opacity="0.75" />

    <!-- 腮红 -->
    <ellipse cx="63" cy="146" rx="9.5" ry="6" fill="#f9bcc4" opacity="0.75" />
    <ellipse cx="137" cy="146" rx="9.5" ry="6" fill="#f9bcc4" opacity="0.75" />

    <!-- 微笑 -->
    <path
      d="M94 146 Q100 152.5 106 146"
      stroke="#22303f" stroke-width="2.6" stroke-linecap="round" fill="none"
    />

    <!-- 围巾 -->
    <path d="M28 172 Q100 197 172 172 L170 185 Q100 210 30 185 Z" fill="url(#scarf)" />
    <path
      d="M48 179 q10 6 20 1 M88 186 q10 6 20 1 M128 182 q10 5 20 0"
      stroke="#cdeee4" stroke-width="2" stroke-linecap="round" fill="none" opacity="0.9"
    />

    <!-- 肚子上的光珠 -->
    <circle cx="100" cy="207" r="14" fill="url(#orbGlow)" filter="url(#orbFilter)" />
    <circle cx="100" cy="207" r="5.4" fill="#fffdf0" opacity="0.95" />

    <!-- 小短脚 -->
    <ellipse cx="72" cy="228" rx="14" ry="8" fill="url(#cloudBody)" />
    <ellipse cx="128" cy="228" rx="14" ry="8" fill="url(#cloudBody)" />
  </svg>
</template>

<script setup>
defineProps({
  size: { type: Number, default: 86 },
  glow: { type: Boolean, default: false }
})
</script>

<style scoped>
.cloud {
  display: block;
  overflow: visible;
}

.floating {
  animation: float 4s ease-in-out infinite;
}

@keyframes float {
  0%, 100% { transform: translateY(0) rotate(0deg); }
  50% { transform: translateY(-6px) rotate(-1.2deg); }
}
</style>
