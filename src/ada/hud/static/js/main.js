/** ADA HUD entry — wire modules once (M13/M14 packaged surface). */

import {
  refreshMode,
  refreshTail,
  startBodyPolls,
  wireBody,
} from "./body.js";
import { wireModeDial } from "./mode.js";
import { wireSession } from "./session.js";
import { wireChat } from "./stream.js";
import { wireXray, xrayList } from "./xray.js";

wireSession({ refreshMode });
wireModeDial();
wireChat({ refreshTail, refreshMode });
wireXray();
wireBody({
  onXrayShow: () => {
    xrayList();
  },
});
startBodyPolls();
