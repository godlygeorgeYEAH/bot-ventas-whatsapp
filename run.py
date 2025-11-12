"""
Script para iniciar la aplicación con soporte de verbosidad

Uso:
    python run.py       # Nivel normal (WARNING)
    python run.py -v    # Nivel INFO
    python run.py -vv   # Nivel DEBUG
    python run.py -vvv  # Nivel TRACE (máximo detalle)
"""
import sys
import uvicorn
from loguru import logger
from config.logging_config import setup_logging

def parse_verbosity():
    """Determina el nivel de verbosidad desde argumentos de CLI"""
    args = sys.argv[1:]
    
    # Contar flags -v
    v_count = 0
    for arg in args:
        if arg in ['-v', '--verbose']:
            v_count = 1
        elif arg == '-vv':
            v_count = 2
        elif arg == '-vvv':
            v_count = 3
    
    # Mapear a niveles de loguru
    levels = {
        0: "WARNING",  # Predeterminado
        1: "INFO",     # -v
        2: "DEBUG",    # -vv
        3: "TRACE"     # -vvv (máximo detalle)
    }
    
    return levels.get(v_count, "WARNING")

if __name__ == "__main__":
    # Determinar nivel de verbosidad
    log_level = parse_verbosity()
    
    # Configurar logging con el nivel apropiado
    setup_logging(level=log_level)
    
    logger.info(f"🚀 Iniciando servidor Uvicorn (log_level={log_level})...")
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="warning"  # Mantener logs de Uvicorn silenciosos
    )