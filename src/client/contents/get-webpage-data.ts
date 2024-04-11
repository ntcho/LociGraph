import type { PlasmoCSConfig } from "plasmo"
import { listen as listenMessage } from "@plasmohq/messaging/message"

import { encode } from 'js-base64';

export const config: PlasmoCSConfig = {
  matches: ["<all_urls>"],
  // all_frames: true
}

const getWebpageData = (): ResponseBody => {
  return {
    url: document.location.href,
    htmlBase64: encode(document.documentElement.outerHTML),
    imageBase64: "",
    language: document.documentElement.lang && "en"
  }
}

export type ResponseBody = {
  url: string
  htmlBase64: string
  imageBase64: string
  language: string
}

// listen for messages from the background script
listenMessage<any, ResponseBody>(async (req, res) => {
  if (req.name === "get-webpage-data") {
    const result = getWebpageData()
    res.send(result)
  }
})