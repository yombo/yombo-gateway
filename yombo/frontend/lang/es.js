export default {
  "commands": {
    "close": {
      "label": "Cerrar"
    }
  },
  "config": {
    "config_item": {
      "yomboapi": {
        "api_key": "Clave de API para usar al hacer solicitudes. Nota: Esta tecla girará para evitar el abuso según sea necesario.",
        "sessionid_key": "Cuando allow_system_session es true, se utiliza para iniciar sesión en la API."
      }
    }
  },
  "lib": {
    "configs": {
      "yombo.ini": {
        "about": "Esto almacena información de configuración de archivos sobre el sistema."
      }
    },
    "state": {
      "amqp.amqpyombo.state": "Verdadero si está conectado, Falso si la conexión no está completamente establecida."
    }
  },
  "lokalise.po.header": "\"MIME-Version: 1.0\\n\"\n\"Content-Type: text\/plain; charset=UTF-8\\n\"\n\"Content-Transfer-Encoding: 8bit\\n\"\n\"X-Generator: lokalise.co\\n\"\n\"Project-Id-Version: Yombo Frontend\\n\"\n\"Report-Msgid-Bugs-To: translate@yombo.net\\n\"\n\"POT-Creation-Date: 2016-10-28 17:12-0400\\n\"\n\"Last-Translator: Mitch Schwenk <translate@yombo.net>\\n\"\n\"Language: es\\n\"\n\"Plural-Forms: nplurals=2; plural=(n!=1);\\n\"",
  "state": {
    "default": {
      "off": "Apagado",
      "on": "Encendido",
      "open": "Abierto",
      "opening": "Abriendo",
      "stopped": "Detenido",
      "unavailable": "Indisponible"
    },
    "lock": {
      "unlocked": "Desbloqueado"
    }
  },
  "system": {
    "current_language": "Español"
  },
  "ui": {
    "common": {
      "enabled": "Habilitado"
    },
    "greeting": {
      "welcome": "Bienvenido"
    },
    "messages": {
      "rate_limit_exceeded": "Demasiados intentos, inténtelo de nuevo más tarde."
    },
    "navigation": {
      "about": "Acerca de",
      "automation": "Automatización",
      "control_tower": "Torre de control",
      "dashboard": "Tablero"
    }
  }
}