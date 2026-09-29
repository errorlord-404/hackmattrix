import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const sourcePath = "C:/Users/prana/Downloads/SIH_Kisan_Sathi_PS-180.pptx";
const presentation = await PresentationFile.importPptx(await FileBlob.load(sourcePath));
const snapshot = await presentation.inspect({
  kind: "slide,textbox,shape,notes,layout",
  maxChars: 60000,
});
console.log(snapshot.ndjson);
