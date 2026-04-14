## POC 구현에 들어가야 할 내용
### 사전구성
1. json format output을 지원하는 LLM API or local model 사용
2. DSL 정의 -> HOME IOT용 DSL 및 function 정의

### 함수 schema
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "SmartHomeFunctionCall",
  "type": "object",
  "additionalProperties": false,
  "properties": {
    "name": {
      "type": "string",
      "enum": [
        "device_control",
        "device_set",
        "schedule_device_control",
        "schedule_device_set"
      ]
    },
    "arguments": {
      "type": "object"
    }
  },
  "required": ["name", "arguments"],
  "oneOf": [
    {
      "properties": {
        "name": { "const": "device_control" },
        "arguments": {
          "type": "object",
          "additionalProperties": false,
          "properties": {
            "device": {
              "type": "string",
              "enum": ["light", "ac", "tv", "speaker"]
            },
            "location": {
              "type": "string",
              "enum": ["living_room", "bedroom", "kitchen"]
            },
            "action": {
              "type": "string",
              "enum": ["on", "off"]
            }
          },
          "required": ["device", "location", "action"]
        }
      }
    },
    {
      "properties": {
        "name": { "const": "device_set" },
        "arguments": {
          "type": "object",
          "additionalProperties": false,
          "properties": {
            "device": {
              "type": "string",
              "enum": ["light", "ac", "tv", "speaker"]
            },
            "location": {
              "type": "string",
              "enum": ["living_room", "bedroom", "kitchen"]
            },
            "property": {
              "type": "string",
              "enum": ["brightness", "temperature", "volume", "color"]
            },
            "value": {
              "type": ["integer", "string"]
            }
          },
          "required": ["device", "location", "property", "value"]
        }
      }
    },
    {
      "properties": {
        "name": { "const": "schedule_device_control" },
        "arguments": {
          "type": "object",
          "additionalProperties": false,
          "properties": {
            "time": {
              "type": "string",
              "pattern": "^([01][0-9]|2[0-3]):[0-5][0-9]$"
            },
            "device": {
              "type": "string",
              "enum": ["light", "ac", "tv", "speaker"]
            },
            "location": {
              "type": "string",
              "enum": ["living_room", "bedroom", "kitchen"]
            },
            "action": {
              "type": "string",
              "enum": ["on", "off"]
            }
          },
          "required": ["time", "device", "location", "action"]
        }
      }
    },
    {
      "properties": {
        "name": { "const": "schedule_device_set" },
        "arguments": {
          "type": "object",
          "additionalProperties": false,
          "properties": {
            "time": {
              "type": "string",
              "pattern": "^([01][0-9]|2[0-3]):[0-5][0-9]$"
            },
            "device": {
              "type": "string",
              "enum": ["light", "ac", "tv", "speaker"]
            },
            "location": {
              "type": "string",
              "enum": ["living_room", "bedroom", "kitchen"]
            },
            "property": {
              "type": "string",
              "enum": ["brightness", "temperature", "volume", "color"]
            },
            "value": {
              "type": ["integer", "string"]
            }
          },
          "required": ["time", "device", "location", "property", "value"]
        }
      }
    }
  ]
}
```

### DSL Schema
```
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "SmartHomeCommand",
  "type": "object",
  "additionalProperties": false,
  "properties": {
    "intent": {
      "type": "string",
      "enum": [
        "device_control",
        "device_set",
        "schedule_device_control",
        "schedule_device_set"
      ]
    },
    "device": {
      "type": "string",
      "enum": ["light", "ac", "tv", "speaker"]
    },
    "location": {
      "type": "string",
      "enum": ["living_room", "bedroom", "kitchen"]
    },
    "action": {
      "type": "string",
      "enum": ["on", "off", "set"]
    },
    "property": {
      "type": ["string", "null"],
      "enum": ["brightness", "temperature", "volume", "color", null]
    },
    "value": {
      "type": ["integer", "string", "null"]
    },
    "time": {
      "type": ["string", "null"],
      "pattern": "^([01][0-9]|2[0-3]):[0-5][0-9]$"
    }
  },
  "required": [
    "intent",
    "device",
    "location",
    "action",
    "property",
    "value",
    "time"
  ],
  "allOf": [
    {
      "if": {
        "properties": {
          "intent": {
            "enum": ["device_control", "schedule_device_control"]
          }
        }
      },
      "then": {
        "properties": {
          "action": { "enum": ["on", "off"] },
          "property": { "const": null },
          "value": { "const": null }
        }
      }
    },
    {
      "if": {
        "properties": {
          "intent": {
            "enum": ["device_set", "schedule_device_set"]
          }
        }
      },
      "then": {
        "properties": {
          "action": { "const": "set" },
          "property": {
            "enum": ["brightness", "temperature", "volume", "color"]
          }
        },
        "required": ["value"]
      }
    },
    {
      "if": {
        "properties": {
          "intent": { "enum": ["device_control", "device_set"] }
        }
      },
      "then": {
        "properties": {
          "time": { "const": null }
        }
      }
    },
    {
      "if": {
        "properties": {
          "intent": {
            "enum": ["schedule_device_control", "schedule_device_set"]
          }
        }
      },
      "then": {
        "properties": {
          "time": {
            "type": "string",
            "pattern": "^([01][0-9]|2[0-3]):[0-5][0-9]$"
          }
        }
      }
    },
    {
      "if": {
        "properties": {
          "property": { "const": "brightness" }
        }
      },
      "then": {
        "properties": {
          "value": {
            "type": "integer",
            "minimum": 0,
            "maximum": 100
          }
        }
      }
    },
    {
      "if": {
        "properties": {
          "property": { "const": "temperature" }
        }
      },
      "then": {
        "properties": {
          "value": {
            "type": "integer",
            "minimum": 16,
            "maximum": 30
          }
        }
      }
    },
    {
      "if": {
        "properties": {
          "property": { "const": "volume" }
        }
      },
      "then": {
        "properties": {
          "value": {
            "type": "integer",
            "minimum": 0,
            "maximum": 100
          }
        }
      }
    },
    {
      "if": {
        "properties": {
          "property": { "const": "color" }
        }
      },
      "then": {
        "properties": {
          "value": {
            "type": "string",
            "enum": ["warm", "cool", "red", "blue"]
          }
        }
      }
    }
  ]
}
```

### DSL -> function EBNF 매핑룰

```
(* SmartHomeCommand DSL -> SmartHomeFunctionCall mapping rules *)

command
  = ctrl_cmd    => {"name":"device_control","arguments":{"device":device,"location":location,"action":action}}
  | set_cmd     => {"name":"device_set","arguments":{"device":device,"location":location,"property":property,"value":value}}
  | sctrl_cmd   => {"name":"schedule_device_control","arguments":{"time":time,"device":device,"location":location,"action":action}}
  | sset_cmd    => {"name":"schedule_device_set","arguments":{"time":time,"device":device,"location":location,"property":property,"value":value}}
  ;

ctrl_cmd   = "CTRL"  "(" device "," location "," action ")" ;
set_cmd    = "SET"   "(" device "," location "," property "," value ")" ;
sctrl_cmd  = "SCTRL" "(" time "," device "," location "," action ")" ;
sset_cmd   = "SSET"  "(" time "," device "," location "," property "," value ")" ;

device     = "light" | "ac" | "tv" | "speaker" ;
location   = "living_room" | "bedroom" | "kitchen" ;
action     = "on" | "off" ;
property   = "brightness" | "temperature" | "volume" | "color" ;
value      = integer | color ;
color      = "warm" | "cool" | "red" | "blue" ;
time       = digit digit ":" digit digit ;
integer    = digit { digit } ;
digit      = "0" | "1" | "2" | "3" | "4" | "5" | "6" | "7" | "8" | "9" ;
```
