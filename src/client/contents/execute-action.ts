import { sendToBackground } from '@plasmohq/messaging';
import { listen as listenMessage } from '@plasmohq/messaging/message';
import type { PlasmoCSConfig } from "plasmo"
import type {
  Command,
  RequestBody as CommandRequestBody,
  ResponseBody as CommandResponseBody
} from '~background/messages/send-command';
import { getActionDescription } from '~lib/utils';

import type { Action } from "~types";

export const config: PlasmoCSConfig = {
  matches: ["<all_urls>"],
  // all_frames: true
}

const getElementByXpath = (path: string): HTMLElement => {
  const element = document.evaluate(
    path,
    document,
    null,
    XPathResult.FIRST_ORDERED_NODE_TYPE,
    null
  ).singleNodeValue as HTMLElement

  return element
}

const clickElement = (element: HTMLElement) => {
  element.click()
  console.info("Clicked element", element);
}

const typeElement = (element: HTMLInputElement, value: string) => {
  element.focus()
  element.value = value
  console.info("Typed value", value, "in element", element);
}

const typeSubmitElement = async (element: HTMLInputElement, value: string) => {
  typeElement(element, value)

  const enterCommands: Command[] = [
    // from https://github.com/ChromeDevTools/devtools-protocol/issues/45#issuecomment-850953391
    {
      method: "Input.dispatchKeyEvent",
      commandParams: { "type": "rawKeyDown", "windowsVirtualKeyCode": 13, "unmodifiedText": "\r", "text": "\r" }
    },
    {
      method: "Input.dispatchKeyEvent",
      commandParams: { "type": "char", "windowsVirtualKeyCode": 13, "unmodifiedText": "\r", "text": "\r" }
    },
    {
      method: "Input.dispatchKeyEvent",
      commandParams: { "type": "keyUp", "windowsVirtualKeyCode": 13, "unmodifiedText": "\r", "text": "\r" }
    },
  ]

  const response = await sendToBackground<CommandRequestBody, CommandResponseBody>({
    name: "send-command",
    body: {
      // from https://stackoverflow.com/a/21983702/4524257
      commands: enterCommands
    }
  })

  if (response.error) {
    console.error("Error while dispatching enter key", response.error)
  } else {
    console.info("Dispatched enter key", response.response)
  }
}

const executeAction = (req: RequestBody): ResponseBody => {
  const action = req.action

  try {
    const element = getElementByXpath(action.element.xpath)

    if (!element) {
      console.error("Element not found", action.element.xpath)
      return { error: `Element not found with xpath=${action.element.xpath}` }
    }

    const actionDescription = getActionDescription(action)

    // confirm before executing action if continuous mode is off
    if (req.continuous || confirm(`Confirm executing action \`${actionDescription}\`?`)) {
      switch (action.type) {
        case "CLICK":
          clickElement(element)
          break
        case "TYPE":
          typeElement(element as HTMLInputElement, action.value)
          break
        case "TYPESUBMIT":
          typeSubmitElement(element as HTMLInputElement, action.value)
          break
        default:
          console.error("Unsupported action type", action.type)
          return { error: "Unsupported action type" }
      }

      console.info(`Executed action \`${actionDescription}\``)

      return { error: null }
    } else {
      console.info(`Cancelled action \`${actionDescription}\``)
      return { error: "Action cancelled" }
    }

  } catch (e) {
    console.error("Error while executing action", e)
    return { error: "Error while executing action" }
  }
}

export type RequestBody = {
  action: Action
  continuous?: boolean
}

export type ResponseBody = {
  error: string | null
}

// listen for messages from the background script
listenMessage<RequestBody, ResponseBody>(async (req, res) => {
  if (req.name === "execute-action") {
    const result = executeAction(req.body)
    res.send(result)
  }
})