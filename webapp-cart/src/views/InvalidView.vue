<template>
  <div class="invalid-container">
    <el-result
      icon="warning"
      title="Link Inválido"
      sub-title="Este link no es válido o ha expirado. Por favor solicita un nuevo link de carrito a través de WhatsApp."
    >
      <template #extra>
        <div class="help-text">
          <p>Para obtener un nuevo link, envía un mensaje a nuestro WhatsApp diciendo:</p>
          <el-card class="example-card">
            <p class="example-message">"Quiero hacer un pedido"</p>
          </el-card>
        </div>
      </template>
    </el-result>
  </div>
</template>

<script setup lang="ts">
// Página que se muestra cuando el link es inválido
</script>

<style scoped>
.invalid-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.help-text {
  text-align: center;
  max-width: 500px;
  margin: 0 auto;
}

.help-text p {
  margin-bottom: 15px;
  font-size: 16px;
  color: #606266;
}

.example-card {
  background-color: #f4f4f5;
  border: 2px dashed #dcdfe6;
}

.example-message {
  font-size: 18px;
  font-weight: 600;
  color: #409eff;
  font-style: italic;
}
</style>

