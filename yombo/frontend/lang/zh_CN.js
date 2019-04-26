export default {
  "commands": {
    "close": {
      "label": "关"
    }
  },
  "config": {
    "config_item": {
      "yomboapi": {
        "api_key": "API密钥在提出请求时使用。注意：该键将旋转以防止滥用。",
        "sessionid_key": "当allow_system_session为true时，这用于登录到API。"
      }
    }
  },
  "lib": {
    "state": {
      "amqp.amqpyombo.state": "如果连接则为真，如果连接未完全建立，则为假。"
    }
  },
  "lokalise.po.header": "\"MIME-Version: 1.0\\n\"\n\"Content-Type: text\/plain; charset=UTF-8\\n\"\n\"Content-Transfer-Encoding: 8bit\\n\"\n\"X-Generator: lokalise.co\\n\"\n\"Project-Id-Version: Yombo Frontend\\n\"\n\"Report-Msgid-Bugs-To: translate@yombo.net\\n\"\n\"POT-Creation-Date: 2016-10-28 17:12-0400\\n\"\n\"Last-Translator: Mitch Schwenk <translate@yombo.net>\\n\"\n\"Language: en\\n\"\n\"Plural-Forms: nplurals=2; plural=(n!=1);\\n\"",
  "state": {
    "default": {
      "off": "关闭",
      "on": "开启",
      "open": "开启",
      "opening": "正在打开",
      "stopped": "已停止",
      "unavailable": "不可用"
    },
    "lock": {
      "unlocked": "解锁"
    }
  },
  "system": {
    "current_language": "中文 (Simplified)"
  },
  "ui": {
    "card": {
      "alarm_control_panel": {
        "arm_away": "离家警戒",
        "arm_home": "在家警戒"
      }
    },
    "common": {
      "disable": "禁用",
      "enable": "启用",
      "enabled": "启用",
      "none": "没有"
    },
    "greeting": {
      "welcome": "欢迎"
    },
    "navigation": {
      "about": "关于",
      "add": "加",
      "automation": "自动化",
      "backup": "备份",
      "control_tower": "控制塔",
      "dashboard": "仪表板"
    }
  }
}