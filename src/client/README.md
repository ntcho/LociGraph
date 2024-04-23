# LociGraph Client

## Development setup

First, run the development server:

```bash
yarn dev
```

Open your browser and load the appropriate development build. For example, if you are developing for the chrome browser, using manifest v3, use: `build/chrome-mv3-dev`.

For further guidance on the framework, [see Plasmo Documentation](https://docs.plasmo.com/)

## Production build

Run the following:

```bash
yarn build
```

This will create a production bundle for your extension in `./build`, ready to be zipped and published to the stores.
