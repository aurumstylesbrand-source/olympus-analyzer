import os from "node:os";
import { syncBuiltinESMExports } from "node:module";
import path from "node:path";

const profileRoot = process.env.OLYMPUS_PROFILE_ROOT;
if (!profileRoot || !path.isAbsolute(profileRoot)) {
  throw new Error("OLYMPUS_PROFILE_ROOT must be an absolute path");
}

// The upstream CLI hardcodes os.homedir()/.shipd/olympus. Override homedir only
// inside this one Node process so two Shipd accounts never share credentials.
os.homedir = () => profileRoot;
syncBuiltinESMExports();
