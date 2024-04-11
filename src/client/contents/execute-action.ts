import { listen as listenMessage } from '@plasmohq/messaging/message';
import type { PlasmoCSConfig } from "plasmo"

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
}

const typeElement = (element: HTMLInputElement, value: string) => {
  element.focus()
  element.value = value
}

const typeSubmitElement = (element: HTMLInputElement, value: string) => {
  element.focus()
  element.value = value
  element.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter" }))
}

const executeAction = (req: RequestBody): ResponseBody => {
  const action = req.action

  try {
    const element = getElementByXpath(action.element.xpath)

    if (confirm(`Execute action: ${action.type} [${action.element.xpath}] ${action.value ? "'" + action.value + "'" : ""}`)) {
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
      return { error: null }
    } else {
      console.info("Action cancelled")
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