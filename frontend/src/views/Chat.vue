<template>
  <div>
    <div class="page-title">AI 健康问答</div>
    <p class="muted">结合你最近一次体检报告作答；没有报告时进入通用健康科普模式。回答不构成医疗诊断。</p>

    <ChatBox
      style="margin-top:16px;"
      height="clamp(520px, calc(100vh - 250px), 900px)"
      placeholder="问点什么吧，例如：我的尿酸升高是什么原因？"
    />
  </div>
</template>

<script setup>
import ChatBox from '@/components/ChatBox.vue'
</script>
